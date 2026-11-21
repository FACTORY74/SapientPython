from scripts.quick_test import example_message

from sapient.codec import FrameDecoder, decode_message, encode_message, frame_payload


def test_message_round_trip() -> None:
    message = example_message()
    assert decode_message(encode_message(message)) == message


def test_fragmented_and_joined_frames() -> None:
    payload = encode_message(example_message())
    combined = frame_payload(payload) + frame_payload(payload)
    decoder = FrameDecoder()
    assert decoder.feed(combined[:5]) == []
    assert decoder.feed(combined[5:]) == [payload, payload]
