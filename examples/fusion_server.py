"""Run a managed fusion-node server until interrupted."""

import asyncio

from sapient.roles import FusionNodeServer

FUSION_ID = "c86a7289-1de9-493a-b17d-0c9f9f9838f4"


async def handle(message, sender) -> None:
    print(message.node_id, message.WhichOneof("content"))


async def main() -> None:
    server = await FusionNodeServer.start(
        "127.0.0.1",
        5020,
        handle,
        fusion_node_id=FUSION_ID,
        manage_registrations=True,
    )
    print("Fusion node listening on 127.0.0.1:5020")
    try:
        await asyncio.Event().wait()
    finally:
        await server.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
