import asyncio
import time

import pytest

from sapient.errors import ProtocolStateError, RegistrationRejectedError
from sapient.messages import Error, RegistrationAck, StatusReport, create_message
from sapient.transports.tcp import open_tcp_connection
from sapient.endpoints import SapientReceiver, SapientSender
from sapient.roles import EdgeNode, EdgeNodeState, FusionNodeServer
from tests.factories import FUSION_ID, NODE_ID, registration, status


def test_successful_initialization_registration_and_goodbye() -> None:
    async def scenario() -> None:
        messages = []
        initial_status = asyncio.Event()
        goodbye = asyncio.Event()

        async def handler(message, sender) -> None:
            messages.append(message)
            if message.WhichOneof("content") == "status_report":
                initial_status.set()
            if (
                message.WhichOneof("content") == "status_report"
                and message.status_report.system == StatusReport.SYSTEM_GOODBYE
            ):
                goodbye.set()

        server = await FusionNodeServer.start(
            "127.0.0.1",
            0,
            handler,
            fusion_node_id=FUSION_ID,
            manage_registrations=True,
        )
        edge = await EdgeNode.connect("127.0.0.1", server.port, node_id=NODE_ID)
        try:
            await edge.initialize(registration(), status())
            await asyncio.wait_for(initial_status.wait(), 1)
            assert edge.state is EdgeNodeState.INITIALIZED
            assert server.registered_nodes[NODE_ID].online
            assert messages[-1].WhichOneof("content") == "status_report"
            await edge.close()
            await asyncio.wait_for(goodbye.wait(), 1)
            for _ in range(100):
                if not server.registered_nodes[NODE_ID].online:
                    break
                await asyncio.sleep(0.001)
            assert not server.registered_nodes[NODE_ID].online
        finally:
            if edge.state is not EdgeNodeState.DISCONNECTED:
                await edge.close(graceful=False)
            await server.close()

    asyncio.run(scenario())


def test_rejected_registration_and_unexpected_order() -> None:
    async def rejected() -> None:
        async def handler(message, sender) -> None:
            await sender.send(
                create_message(
                    sender_id=FUSION_ID,
                    destination_id=message.node_id,
                    content=RegistrationAck(
                        acceptance=False,
                        ack_response_reason=["not permitted"],
                    ),
                )
            )

        server = await FusionNodeServer.start("127.0.0.1", 0, handler)
        edge = await EdgeNode.connect("127.0.0.1", server.port, node_id=NODE_ID)
        try:
            with pytest.raises(RegistrationRejectedError, match="not permitted"):
                await edge.initialize(registration(), status())
        finally:
            await edge.close(graceful=False)
            await server.close()

    async def wrong_message() -> None:
        async def handler(message, sender) -> None:
            await sender.send(
                create_message(sender_id=FUSION_ID, content=status())
            )

        server = await FusionNodeServer.start("127.0.0.1", 0, handler)
        edge = await EdgeNode.connect("127.0.0.1", server.port, node_id=NODE_ID)
        try:
            with pytest.raises(ProtocolStateError, match="Expected registration_ack"):
                await edge.initialize(registration(), status())
        finally:
            await edge.close(graceful=False)
            await server.close()

    asyncio.run(rejected())
    asyncio.run(wrong_message())


def test_registration_timeout_reconnects_and_resends() -> None:
    async def scenario() -> None:
        registrations = 0

        async def handler(message, sender) -> None:
            nonlocal registrations
            registrations += 1
            if registrations == 2:
                await sender.send(
                    create_message(
                        sender_id=FUSION_ID,
                        destination_id=message.node_id,
                        content=RegistrationAck(acceptance=True),
                    )
                )

        server = await FusionNodeServer.start("127.0.0.1", 0, handler)
        edge = await EdgeNode.connect("127.0.0.1", server.port, node_id=NODE_ID)
        try:
            await edge.initialize(registration(), status(), timeout=0.02)
            assert registrations == 2
            assert edge.state is EdgeNodeState.INITIALIZED
        finally:
            await edge.close(graceful=False)
            await server.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("response_kind", ["wrong_destination", "wrong_peer", "error"])
def test_registration_rejects_unmatched_or_error_responses(response_kind: str) -> None:
    async def scenario() -> None:
        async def handler(message, sender) -> None:
            if response_kind == "error":
                content = Error(packet=b"registration", error_message=["invalid registration"])
                destination = NODE_ID
                sender_id = FUSION_ID
            else:
                content = RegistrationAck(acceptance=True)
                destination = FUSION_ID if response_kind == "wrong_destination" else NODE_ID
                sender_id = NODE_ID if response_kind == "wrong_peer" else FUSION_ID
            await sender.send(
                create_message(
                    sender_id=sender_id,
                    destination_id=destination,
                    content=content,
                )
            )

        server = await FusionNodeServer.start("127.0.0.1", 0, handler)
        edge = await EdgeNode.connect(
            "127.0.0.1",
            server.port,
            node_id=NODE_ID,
            expected_fusion_node_id=FUSION_ID,
        )
        try:
            expected = {
                "wrong_destination": "destination_id",
                "wrong_peer": "unexpected node",
                "error": "invalid registration",
            }[response_kind]
            with pytest.raises(ProtocolStateError, match=expected):
                await edge.initialize(registration(), status())
        finally:
            await edge.close(graceful=False)
            await server.close()

    asyncio.run(scenario())


def test_short_reconnect_preserves_registration_and_long_reconnect_registers() -> None:
    async def scenario() -> None:
        received = []
        received_event = asyncio.Event()

        async def handler(message, sender) -> None:
            received.append(message.WhichOneof("content"))
            received_event.set()

        async def wait_for_count(expected: int) -> None:
            while received.count("status_report") < expected:
                received_event.clear()
                await asyncio.wait_for(received_event.wait(), 1)

        server = await FusionNodeServer.start(
            "127.0.0.1", 0, handler, fusion_node_id=FUSION_ID, manage_registrations=True
        )
        edge = await EdgeNode.connect("127.0.0.1", server.port, node_id=NODE_ID)
        try:
            await edge.initialize(registration(), status())
            await wait_for_count(1)
            await edge.connection.close()
            await edge.reconnect(disconnected_at=time.monotonic(), retry_interval=0)
            assert edge.state is EdgeNodeState.INITIALIZED
            await wait_for_count(2)
            await edge.connection.close()
            await edge.reconnect(
                disconnected_at=time.monotonic() - 121,
                retry_interval=0,
                reregister_after=120,
            )
            assert edge.state is EdgeNodeState.INITIALIZED
            await wait_for_count(3)
            assert received.count("status_report") >= 3
        finally:
            await edge.close(graceful=False)
            await server.close()

    asyncio.run(scenario())


def test_reconnect_limits_and_cancellation() -> None:
    async def scenario() -> None:
        async def handler(message, sender) -> None:
            pass

        server = await FusionNodeServer.start(
            "127.0.0.1", 0, handler, fusion_node_id=FUSION_ID, manage_registrations=True
        )
        port = server.port
        edge = await EdgeNode.connect("127.0.0.1", port, node_id=NODE_ID)
        await edge.initialize(registration(), status())
        await edge.connection.close()
        await server.close()
        with pytest.raises(OSError):
            await edge.reconnect(retry_interval=0, max_attempts=1)

        cancelled = asyncio.Event()
        cancelled.set()
        with pytest.raises(asyncio.CancelledError):
            await edge.reconnect(retry_interval=0, cancel_event=cancelled)

    asyncio.run(scenario())


def test_managed_server_rejects_unregistered_operational_messages() -> None:
    async def scenario() -> None:
        async def handler(message, sender) -> None:
            raise AssertionError("unregistered message reached application handler")

        server = await FusionNodeServer.start(
            "127.0.0.1", 0, handler, fusion_node_id=FUSION_ID, manage_registrations=True
        )
        connection = await open_tcp_connection("127.0.0.1", server.port)
        sender = SapientSender(connection)
        receiver = SapientReceiver(connection)
        try:
            await sender.send(create_message(sender_id=NODE_ID, content=status()))
            response = await asyncio.wait_for(receiver.receive(), 1)
            assert response.WhichOneof("content") == "error"
            assert "must register" in response.error.error_message[0]
        finally:
            await connection.close()
            await server.close()

    asyncio.run(scenario())
