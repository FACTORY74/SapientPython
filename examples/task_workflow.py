"""Track acceptance and completion of a SAPIENT task."""

import asyncio

from sapient.messages import TaskAck
from sapient.roles import AcknowledgementTracker
from _fixtures import ULID


async def main() -> None:
    tracker = AcknowledgementTracker()
    workflow = tracker.track_task(ULID)
    tracker.handle_task_ack(
        TaskAck(task_id=ULID, task_status=TaskAck.TASK_STATUS_ACCEPTED)
    )
    print("First update:", (await workflow.wait(timeout=1)).task_status)
    tracker.handle_task_ack(
        TaskAck(task_id=ULID, task_status=TaskAck.TASK_STATUS_COMPLETED)
    )
    print("Final state:", workflow.state.value)


if __name__ == "__main__":
    asyncio.run(main())
