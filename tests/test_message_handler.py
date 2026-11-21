import asyncio

import pytest

from sapient.errors import UnknownDestinationError
from sapient.messages import create_message
from sapient.roles import TransparentMessageHandler
from tests.factories import FUSION_ID, NODE_ID, registration, status


class RecordingSender:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, message) -> None:
        self.messages.append(message.SerializeToString())


def test_transparent_routing_registration_persistence_and_unknown_destination() -> None:
    async def scenario() -> None:
        persisted = []
        unknown = []
        fusion = RecordingSender()
        edge = RecordingSender()
        router = TransparentMessageHandler(
            fusion_node_id=FUSION_ID,
            persistence_hook=lambda message: persisted.append(message.SerializeToString()),
            unknown_destination_hook=lambda message: unknown.append(message.node_id),
        )
        router.register(FUSION_ID, fusion)
        router.register(NODE_ID, edge)

        registration_message = create_message(sender_id=NODE_ID, content=registration())
        original = registration_message.SerializeToString()
        await router.route(registration_message)
        assert fusion.messages == [original]
        assert registration_message.SerializeToString() == original

        status_message = create_message(
            sender_id=FUSION_ID,
            destination_id=NODE_ID,
            content=status(),
        )
        await router.route(status_message)
        assert edge.messages == [status_message.SerializeToString()]
        assert len(persisted) == 2

        router.unregister(NODE_ID)
        with pytest.raises(UnknownDestinationError):
            await router.route(status_message)
        assert unknown == [FUSION_ID]

    asyncio.run(scenario())
