"""Connect and initialize an edge node against examples/fusion_server.py."""

import asyncio

from sapient.roles import EdgeNode
from _fixtures import NODE_ID, registration, status


async def main() -> None:
    async with await EdgeNode.connect(
        "127.0.0.1", 5020, node_id=NODE_ID
    ) as edge:
        await edge.initialize(registration(), status())
        print("Edge node initialized; press Ctrl+C to send GOODBYE and stop")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
