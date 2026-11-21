"""Client-side edge-node lifecycle and reconnection policy."""

import asyncio
import time
from enum import Enum, auto
from ssl import SSLContext

from sapient.endpoints import SapientReceiver, SapientSender
from sapient.errors import ProtocolStateError, RegistrationRejectedError
from sapient.messages import Registration, StatusReport, create_message
from sapient.messages.identifiers import new_ulid
from sapient.transports.tcp import TcpConnection, open_tcp_connection
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage


class EdgeNodeState(Enum):
    CONNECTED = auto()
    REGISTERING = auto()
    INITIALIZED = auto()
    DISCONNECTED = auto()
    CLOSING = auto()


class EdgeNode:
    def __init__(
        self,
        connection: TcpConnection,
        *,
        host: str | None = None,
        port: int | None = None,
        node_id: str | None = None,
        ssl_context: SSLContext | None = None,
        expected_fusion_node_id: str | None = None,
    ) -> None:
        self.connection = connection
        self.sender = SapientSender(connection)
        self.receiver = SapientReceiver(connection)
        self.host = host
        self.port = port
        self.node_id = node_id
        self.ssl_context = ssl_context
        self.expected_fusion_node_id = expected_fusion_node_id
        self.state = EdgeNodeState.CONNECTED
        self.fusion_node_id: str | None = None
        self.registration: Registration | None = None
        self.initial_status: StatusReport | None = None

    @classmethod
    async def connect(
        cls,
        host: str,
        port: int,
        *,
        node_id: str | None = None,
        ssl_context: SSLContext | None = None,
        expected_fusion_node_id: str | None = None,
    ) -> "EdgeNode":
        connection = await open_tcp_connection(
            host,
            port,
            ssl_context=ssl_context,
            server_hostname=host if ssl_context else None,
        )
        return cls(
            connection,
            host=host,
            port=port,
            node_id=node_id,
            ssl_context=ssl_context,
            expected_fusion_node_id=expected_fusion_node_id,
        )

    async def initialize(
        self,
        registration: Registration,
        initial_status: StatusReport,
        *,
        timeout: float = 30,
        max_attempts: int = 2,
    ) -> None:
        if self.state is not EdgeNodeState.CONNECTED:
            raise ProtocolStateError(f"Cannot initialize while {self.state.name.lower()}")
        if self.node_id is None:
            raise ProtocolStateError("node_id is required for initialization")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        response = None
        for attempt in range(1, max_attempts + 1):
            self.state = EdgeNodeState.REGISTERING
            await self.send(create_message(sender_id=self.node_id, content=registration))
            try:
                response = await asyncio.wait_for(self.receive(), timeout)
                break
            except TimeoutError:
                await self.connection.close()
                self.state = EdgeNodeState.DISCONNECTED
                if attempt >= max_attempts:
                    raise
                if self.host is None or self.port is None:
                    raise ProtocolStateError(
                        "Registration timeout recovery requires a host and port"
                    )
                self.connection = await open_tcp_connection(
                    self.host,
                    self.port,
                    ssl_context=self.ssl_context,
                    server_hostname=self.host if self.ssl_context else None,
                )
                self.sender = SapientSender(self.connection)
                self.receiver = SapientReceiver(self.connection)
                self.state = EdgeNodeState.CONNECTED
            except BaseException:
                self.state = EdgeNodeState.CONNECTED
                raise

        assert response is not None
        content = response.WhichOneof("content")
        if content == "error":
            self.state = EdgeNodeState.CONNECTED
            reasons = "; ".join(response.error.error_message)
            raise ProtocolStateError(reasons or "Registration failed with a SAPIENT error")
        if content != "registration_ack":
            self.state = EdgeNodeState.CONNECTED
            raise ProtocolStateError("Expected registration_ack during initialization")
        if not response.HasField("destination_id") or response.destination_id != self.node_id:
            self.state = EdgeNodeState.CONNECTED
            raise ProtocolStateError("Registration acknowledgement has the wrong destination_id")
        expected_peer = self.expected_fusion_node_id or self.fusion_node_id
        if expected_peer is not None and response.node_id != expected_peer:
            self.state = EdgeNodeState.CONNECTED
            raise ProtocolStateError("Registration acknowledgement came from an unexpected node")
        if not response.registration_ack.acceptance:
            self.state = EdgeNodeState.CONNECTED
            reasons = "; ".join(response.registration_ack.ack_response_reason)
            raise RegistrationRejectedError(reasons or "Registration rejected")
        self.fusion_node_id = response.node_id
        await self.send(
            create_message(
                sender_id=self.node_id,
                destination_id=self.fusion_node_id,
                content=initial_status,
            )
        )
        self.registration = Registration()
        self.registration.CopyFrom(registration)
        self.initial_status = StatusReport()
        self.initial_status.CopyFrom(initial_status)
        self.state = EdgeNodeState.INITIALIZED

    async def reconnect(
        self,
        *,
        disconnected_at: float | None = None,
        retry_interval: float = 10,
        reregister_after: float = 120,
        max_attempts: int | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> None:
        if self.host is None or self.port is None:
            raise ProtocolStateError("Reconnect requires a host and port")
        if self.registration is None or self.initial_status is None or self.node_id is None:
            raise ProtocolStateError("Reconnect requires a previously initialized node")
        lost_at = disconnected_at if disconnected_at is not None else time.monotonic()
        self.state = EdgeNodeState.DISCONNECTED
        attempts = 0
        while max_attempts is None or attempts < max_attempts:
            if cancel_event is not None and cancel_event.is_set():
                raise asyncio.CancelledError
            attempts += 1
            try:
                connection = await open_tcp_connection(
                    self.host,
                    self.port,
                    ssl_context=self.ssl_context,
                    server_hostname=self.host if self.ssl_context else None,
                )
            except OSError:
                if max_attempts is not None and attempts >= max_attempts:
                    raise
                if cancel_event is None:
                    await asyncio.sleep(retry_interval)
                else:
                    try:
                        await asyncio.wait_for(cancel_event.wait(), retry_interval)
                    except TimeoutError:
                        pass
                continue
            self.connection = connection
            self.sender = SapientSender(connection)
            self.receiver = SapientReceiver(connection)
            self.state = EdgeNodeState.CONNECTED
            if time.monotonic() - lost_at >= reregister_after:
                await self.initialize(self.registration, self.initial_status)
            else:
                self.state = EdgeNodeState.INITIALIZED
                await self.send(
                    create_message(
                        sender_id=self.node_id,
                        destination_id=self.fusion_node_id,
                        content=self.initial_status,
                    )
                )
            return
        raise ConnectionError("Reconnect attempts exhausted")

    async def send(self, message: SapientMessage) -> None:
        if self.state in {EdgeNodeState.DISCONNECTED, EdgeNodeState.CLOSING}:
            raise ProtocolStateError(f"Cannot send while {self.state.name.lower()}")
        await self.sender.send(message)

    async def receive(self) -> SapientMessage:
        return await self.receiver.receive()

    async def close(self, *, graceful: bool = True) -> None:
        if self.state is EdgeNodeState.CLOSING:
            return
        was_initialized = self.state is EdgeNodeState.INITIALIZED
        self.state = EdgeNodeState.CLOSING
        if graceful and was_initialized and self.node_id and self.initial_status:
            goodbye = StatusReport(
                report_id=new_ulid(),
                system=StatusReport.SYSTEM_GOODBYE,
                info=StatusReport.INFO_NEW,
                mode=self.initial_status.mode,
            )
            await self.sender.send(
                create_message(
                    sender_id=self.node_id,
                    destination_id=self.fusion_node_id,
                    content=goodbye,
                )
            )
        await self.connection.close()
        self.state = EdgeNodeState.DISCONNECTED

    async def __aenter__(self) -> "EdgeNode":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.close(graceful=exc is None)
