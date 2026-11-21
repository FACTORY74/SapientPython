"""Fast end-to-end SAPIENT interface validation harness."""

import asyncio
from uuid import UUID

from sapient.codec import FrameDecoder, decode_message, encode_message, frame_payload
from sapient.messages import StatusReport, create_message
from sapient.roles import EdgeNode, FusionNodeServer

NODE_ID = "5ea410b7-9656-4d22-929d-3bad7bf15a21"
FUSION_ID = "c86a7289-1de9-493a-b17d-0c9f9f9838f4"
REPORT_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def example_message():
    status = StatusReport(
        report_id=REPORT_ID,
        system=StatusReport.SYSTEM_OK,
        info=StatusReport.INFO_NEW,
        mode="default",
    )
    return create_message(
        sender_id=NODE_ID,
        destination_id=FUSION_ID,
        content=status,
    )


def check_codec_and_framing() -> None:
    original = example_message()
    payload = encode_message(original)
    restored = decode_message(payload)
    assert restored == original

    framed = frame_payload(payload)
    decoder = FrameDecoder()
    assert decoder.feed(framed[:3]) == []
    assert decoder.feed(framed[3:8]) == []
    assert decoder.feed(framed[8:]) == [payload]
    assert decoder.pending_bytes == 0


async def check_tcp_loopback() -> None:
    received = asyncio.Event()

    async def handler(message, sender) -> None:
        assert UUID(message.node_id) == UUID(NODE_ID)
        assert message.WhichOneof("content") == "status_report"
        await sender.send(message)
        received.set()

    server = await FusionNodeServer.start("127.0.0.1", 0, handler)
    try:
        async with await EdgeNode.connect("127.0.0.1", server.port) as edge:
            message = example_message()
            await edge.send(message)
            echoed = await asyncio.wait_for(edge.receive(), timeout=2)
            assert echoed == message
            await asyncio.wait_for(received.wait(), timeout=2)
    finally:
        await server.close()


def main() -> None:
    check_codec_and_framing()
    asyncio.run(check_tcp_loopback())
    print("SAPIENT quick test passed: validation, protobuf, framing, and TCP loopback")


if __name__ == "__main__":
    main()
