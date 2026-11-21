"""Example effector that accepts and completes tasks sent by C2."""

import asyncio

from sapient.messages import Registration, TaskAck, create_message
from sapient.roles import EdgeNode

from examples.roles.common import C2_ID, EFFECTOR_ID, HOST, PORT, registration, status


async def send_ack(edge: EdgeNode, task_id: str, task_status: int) -> None:
    await edge.send(
        create_message(
            sender_id=EFFECTOR_ID,
            destination_id=C2_ID,
            content=TaskAck(task_id=task_id, task_status=task_status),
        )
    )


async def main() -> None:
    edge = await EdgeNode.connect(HOST, PORT, node_id=EFFECTOR_ID)
    try:
        await edge.initialize(
            registration("Demo mobile effector", Registration.NODE_TYPE_KINETIC, "tasking"),
            status(),
        )
        print("EFFECTOR registered; waiting for a task")

        while True:
            message = await edge.receive()
            if message.WhichOneof("content") != "task":
                print("EFFECTOR received", message.WhichOneof("content"))
                continue

            task = message.task
            print(f"EFFECTOR accepted task {task.task_id}: {task.command.request}")
            await send_ack(edge, task.task_id, TaskAck.TASK_STATUS_ACCEPTED)
            await asyncio.sleep(1)  # stand-in for real effector activity
            await send_ack(edge, task.task_id, TaskAck.TASK_STATUS_COMPLETED)
            print(f"EFFECTOR completed task {task.task_id}")
    finally:
        await edge.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
