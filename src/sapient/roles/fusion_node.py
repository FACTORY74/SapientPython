"""Concurrent fusion-node server with optional managed registration state."""

import asyncio
import ssl
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sapient.endpoints import SapientReceiver, SapientSender
from sapient.errors import ProtocolStateError
from sapient.messages import Error, Registration, RegistrationAck, create_message
from sapient.transports.tcp import TcpConnection
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

MessageHandler = Callable[[SapientMessage, SapientSender], Awaitable[None]]
ErrorHandler = Callable[[BaseException], None]


@dataclass
class RegisteredNode:
    node_id: str
    registration: Registration
    online: bool = False
    active_sessions: int = 0


class FusionNodeServer:
    def __init__(
        self,
        server: asyncio.Server,
        *,
        fusion_node_id: str | None,
        manage_registrations: bool,
    ) -> None:
        self._server = server
        self.fusion_node_id = fusion_node_id
        self.manage_registrations = manage_registrations
        self.registered_nodes: dict[str, RegisteredNode] = {}
        self._connections: set[TcpConnection] = set()
        self._tasks: set[asyncio.Task] = set()
        self.errors: list[BaseException] = []

    @classmethod
    async def start(
        cls,
        host: str,
        port: int,
        handler: MessageHandler,
        *,
        fusion_node_id: str | None = None,
        manage_registrations: bool = False,
        ssl_context: ssl.SSLContext | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> "FusionNodeServer":
        if manage_registrations and fusion_node_id is None:
            raise ValueError("fusion_node_id is required for managed registration")
        instance: FusionNodeServer | None = None

        async def accept(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            assert instance is not None
            task = asyncio.current_task()
            connection = TcpConnection(reader, writer)
            instance._connections.add(connection)
            if task is not None:
                instance._tasks.add(task)
            receiver = SapientReceiver(connection)
            sender = SapientSender(connection)
            session_node_id: str | None = None
            try:
                async for message in receiver:
                    if instance.manage_registrations:
                        resolved_node_id = await instance._managed_message(
                            message, sender, session_node_id
                        )
                        if session_node_id is None:
                            session_node_id = resolved_node_id
                            registered = instance.registered_nodes[session_node_id]
                            registered.active_sessions += 1
                            registered.online = True
                        if message.WhichOneof("content") == "registration":
                            continue
                    await handler(message, sender)
            except BaseException as exc:
                if not isinstance(exc, asyncio.CancelledError):
                    instance.errors.append(exc)
                    if error_handler is not None:
                        error_handler(exc)
            finally:
                if session_node_id in instance.registered_nodes:
                    registered = instance.registered_nodes[session_node_id]
                    registered.active_sessions = max(0, registered.active_sessions - 1)
                    registered.online = registered.active_sessions > 0
                instance._connections.discard(connection)
                if task is not None:
                    instance._tasks.discard(task)
                await connection.close()

        server = await asyncio.start_server(accept, host, port, ssl=ssl_context)
        instance = cls(
            server,
            fusion_node_id=fusion_node_id,
            manage_registrations=manage_registrations,
        )
        return instance

    async def _managed_message(
        self,
        message: SapientMessage,
        sender: SapientSender,
        session_node_id: str | None,
    ) -> str:
        content = message.WhichOneof("content")
        node_id = message.node_id
        if session_node_id is not None and node_id != session_node_id:
            raise ProtocolStateError(
                f"Connection registered as {session_node_id} cannot send as {node_id}"
            )
        if content == "registration":
            registration = Registration()
            registration.CopyFrom(message.registration)
            previous = self.registered_nodes.get(node_id)
            active_sessions = previous.active_sessions if previous else 0
            self.registered_nodes[node_id] = RegisteredNode(
                node_id, registration, active_sessions > 0, active_sessions
            )
            acknowledgement = RegistrationAck(acceptance=True)
            await sender.send(
                create_message(
                    sender_id=self.fusion_node_id,
                    destination_id=node_id,
                    content=acknowledgement,
                )
            )
            return node_id
        registered = self.registered_nodes.get(node_id)
        if registered is None:
            error = Error(
                packet=message.SerializeToString(),
                error_message=["Node must register before sending operational messages"],
            )
            await sender.send(
                create_message(
                    sender_id=self.fusion_node_id,
                    destination_id=node_id,
                    content=error,
                )
            )
            raise ProtocolStateError(f"Unregistered node {node_id} sent {content}")
        registered.online = True
        return node_id

    @property
    def active_connection_count(self) -> int:
        return len(self._connections)

    @property
    def port(self) -> int:
        sockets = self._server.sockets or []
        if not sockets:
            raise RuntimeError("Server has no listening socket")
        return int(sockets[0].getsockname()[1])

    async def close(self, *, timeout: float = 5) -> None:
        self._server.close()
        connections = tuple(self._connections)
        if connections:
            await asyncio.gather(
                *(connection.close(timeout=min(timeout, 1)) for connection in connections),
                return_exceptions=True,
            )
        current = asyncio.current_task()
        tasks = [task for task in self._tasks if task is not current]
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=timeout)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        await asyncio.wait_for(self._server.wait_closed(), timeout)

    async def __aenter__(self) -> "FusionNodeServer":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.close()
