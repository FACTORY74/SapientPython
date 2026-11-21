"""Run a complete local registration, initial status, and GOODBYE exchange."""

import asyncio

from sapient.roles import EdgeNode, FusionNodeServer
from _fixtures import FUSION_ID, NODE_ID, registration, status


async def main() -> None:
    received = []

    async def handle(message, sender) -> None:
        received.append(message.WhichOneof("content"))

    server = await FusionNodeServer.start(
        "127.0.0.1",
        0,
        handle,
        fusion_node_id=FUSION_ID,
        manage_registrations=True,
    )
    edge = await EdgeNode.connect("127.0.0.1", server.port, node_id=NODE_ID)
    try:
        await edge.initialize(registration(), status())
        print("Registered:", server.registered_nodes[NODE_ID].registration.name)
        await edge.close()
        await asyncio.sleep(0.01)
        print("Operational messages:", received)
    finally:
        await server.close()


if __name__ == "__main__":
    asyncio.run(main())
