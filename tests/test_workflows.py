import asyncio

import pytest

from sapient.errors import ProtocolStateError, UnexpectedAcknowledgementError
from sapient.messages import AlertAck, TaskAck
from sapient.roles import AcknowledgementTracker, AlertState, TaskState
from tests.factories import ULID


def test_task_acknowledgement_lifecycle_and_waiting() -> None:
    async def scenario() -> None:
        tracker = AcknowledgementTracker()
        workflow = tracker.track_task(ULID)
        accepted = TaskAck(task_id=ULID, task_status=TaskAck.TASK_STATUS_ACCEPTED)
        tracker.handle_task_ack(accepted)
        assert workflow.state is TaskState.ACCEPTED
        assert await workflow.wait(timeout=1) == accepted
        completed = TaskAck(task_id=ULID, task_status=TaskAck.TASK_STATUS_COMPLETED)
        tracker.handle_task_ack(completed)
        assert workflow.state is TaskState.COMPLETED

    asyncio.run(scenario())


def test_alert_acknowledgement_and_unexpected_ids() -> None:
    tracker = AcknowledgementTracker()
    workflow = tracker.track_alert(ULID)
    tracker.handle_alert_ack(
        AlertAck(alert_id=ULID, alert_ack_status=AlertAck.ALERT_ACK_STATUS_ACCEPTED)
    )
    assert workflow.state is AlertState.ACCEPTED
    with pytest.raises(ProtocolStateError, match="already resolved"):
        tracker.handle_alert_ack(
            AlertAck(alert_id=ULID, alert_ack_status=AlertAck.ALERT_ACK_STATUS_CANCELLED)
        )
    with pytest.raises(UnexpectedAcknowledgementError):
        tracker.handle_task_ack(
            TaskAck(
                task_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
                task_status=TaskAck.TASK_STATUS_ACCEPTED,
            )
        )
