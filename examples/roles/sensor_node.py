"""Example sensor that registers and publishes three observations."""

import asyncio

from sapient.messages import Registration, create_message, new_ulid
from sapient.roles import EdgeNode

from examples.roles.common import C2_ID, HOST, PORT, SENSOR_ID, detection, registration, status


async def main() -> None:
    edge = await EdgeNode.connect(HOST, PORT, node_id=SENSOR_ID)
    try:
        await edge.initialize(
            registration("Demo camera sensor", Registration.NODE_TYPE_CAMERA, "detection"),
            status(),
        )
        print("SENSOR registered with C2")

        # A stable object_id links these source observations. Whether observations
        # from other sensors belong to the same fused track is an application decision.
        object_id = new_ulid()
        for sequence in range(3):
            report = detection(
                object_id,
                longitude=-3.3929 + sequence * 0.001,
                latitude=53.1069 + sequence * 0.0005,
            )
            await edge.send(
                create_message(
                    sender_id=SENSOR_ID,
                    destination_id=C2_ID,
                    content=report,
                )
            )
            print(f"SENSOR sent detection {sequence + 1}: object_id={object_id}")
            await asyncio.sleep(1)
    finally:
        await edge.close()


if __name__ == "__main__":
    asyncio.run(main())
