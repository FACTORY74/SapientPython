"""Transparent destination-based routing for SAPIENT envelopes."""

import inspect
from collections.abc import Awaitable, Callable

from sapient.endpoints import SapientSender
from sapient.errors import UnknownDestinationError
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

PersistenceHook = Callable[[SapientMessage], Awaitable[None] | None]
UnknownDestinationHook = Callable[[SapientMessage], Awaitable[None] | None]


class TransparentMessageHandler:
    """Route envelopes without modifying their protobuf content."""

    def __init__(
        self,
        *,
        fusion_node_id: str,
        persistence_hook: PersistenceHook | None = None,
        unknown_destination_hook: UnknownDestinationHook | None = None,
    ) -> None:
        self.fusion_node_id = fusion_node_id
        self.persistence_hook = persistence_hook
        self.unknown_destination_hook = unknown_destination_hook
        self._senders: dict[str, SapientSender] = {}

    def register(self, node_id: str, sender: SapientSender) -> None:
        self._senders[node_id] = sender

    def unregister(self, node_id: str, sender: SapientSender | None = None) -> None:
        if sender is None or self._senders.get(node_id) is sender:
            self._senders.pop(node_id, None)

    async def _invoke(self, hook, message: SapientMessage) -> None:
        if hook is not None:
            result = hook(message)
            if inspect.isawaitable(result):
                await result

    async def route(self, message: SapientMessage) -> None:
        await self._invoke(self.persistence_hook, message)
        destination = message.destination_id if message.HasField("destination_id") else None
        if not destination and message.WhichOneof("content") == "registration":
            destination = self.fusion_node_id
        sender = self._senders.get(destination or "")
        if sender is None:
            await self._invoke(self.unknown_destination_hook, message)
            raise UnknownDestinationError(
                f"No connected node for destination {destination or '<unspecified>'}"
            )
        await sender.send(message)
