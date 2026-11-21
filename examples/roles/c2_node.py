"""Example C2/fusion node that receives detections and tasks an effector."""

import asyncio

from sapient.messages import create_message
from sapient.roles import AcknowledgementTracker, FusionNodeServer

from examples.roles.common import C2_ID, EFFECTOR_ID, HOST, PORT, inspect_task


async def main() -> None:
    tracker = AcknowledgementTracker()
    senders = {}
    task_sent = False

    async def handle(message, sender) -> None:
        nonlocal task_sent
        content = message.WhichOneof("content")

        # The first operational message follows registration, so it also makes
        # the connection's reply sender available to this small demonstration.
        senders[message.node_id] = sender

        if content == "status_report":
            print(f"C2 node online: {message.node_id}")
        elif content == "detection_report":
            report = message.detection_report
            print(
                "C2 detection:",
                f"object_id={report.object_id}",
                f"lon={report.location.x:.4f}",
                f"lat={report.location.y:.4f}",
            )
        elif content == "task_ack":
            workflow = tracker.handle_task_ack(message.task_ack)
            print(f"C2 task {workflow.task_id}: {workflow.state.value}")

        if not task_sent and EFFECTOR_ID in senders:
            task = inspect_task()
            tracker.track_task(task.task_id)
            await senders[EFFECTOR_ID].send(
                create_message(
                    sender_id=C2_ID,
                    destination_id=EFFECTOR_ID,
                    content=task,
                )
            )
            task_sent = True
            print(f"C2 sent task {task.task_id} to effector")

    server = await FusionNodeServer.start(
        HOST,
        PORT,
        handle,
        fusion_node_id=C2_ID,
        manage_registrations=True,
    )
    print(f"C2 listening on {HOST}:{PORT}; press Ctrl+C to stop")
    try:
        await asyncio.Event().wait()
    finally:
        await server.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
