"""Correlation and state transitions for task and alert acknowledgements."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum

from sapient.errors import ProtocolStateError, UnexpectedAcknowledgementError
from sapient_msg.bsi_flex_335_v2_0.alert_ack_pb2 import AlertAck
from sapient_msg.bsi_flex_335_v2_0.task_ack_pb2 import TaskAck


class TaskState(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class AlertState(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class TaskWorkflow:
    task_id: str
    state: TaskState = TaskState.PENDING
    updates: asyncio.Queue[TaskAck] = field(default_factory=asyncio.Queue)

    async def wait(self, timeout: float | None = None) -> TaskAck:
        operation = self.updates.get()
        return await asyncio.wait_for(operation, timeout) if timeout else await operation


@dataclass
class AlertWorkflow:
    alert_id: str
    state: AlertState = AlertState.PENDING
    updates: asyncio.Queue[AlertAck] = field(default_factory=asyncio.Queue)

    async def wait(self, timeout: float | None = None) -> AlertAck:
        operation = self.updates.get()
        return await asyncio.wait_for(operation, timeout) if timeout else await operation


class AcknowledgementTracker:
    def __init__(self) -> None:
        self.tasks: dict[str, TaskWorkflow] = {}
        self.alerts: dict[str, AlertWorkflow] = {}

    def track_task(self, task_id: str) -> TaskWorkflow:
        if task_id in self.tasks:
            raise ProtocolStateError(f"Task {task_id} is already tracked")
        workflow = TaskWorkflow(task_id)
        self.tasks[task_id] = workflow
        return workflow

    def track_alert(self, alert_id: str) -> AlertWorkflow:
        if alert_id in self.alerts:
            raise ProtocolStateError(f"Alert {alert_id} is already tracked")
        workflow = AlertWorkflow(alert_id)
        self.alerts[alert_id] = workflow
        return workflow

    def handle_task_ack(self, acknowledgement: TaskAck) -> TaskWorkflow:
        workflow = self.tasks.get(acknowledgement.task_id)
        if workflow is None:
            raise UnexpectedAcknowledgementError(
                f"No tracked task matches {acknowledgement.task_id}"
            )
        states = {
            TaskAck.TASK_STATUS_ACCEPTED: TaskState.ACCEPTED,
            TaskAck.TASK_STATUS_REJECTED: TaskState.REJECTED,
            TaskAck.TASK_STATUS_COMPLETED: TaskState.COMPLETED,
            TaskAck.TASK_STATUS_FAILED: TaskState.FAILED,
        }
        new_state = states[acknowledgement.task_status]
        allowed = {
            TaskState.PENDING: {TaskState.ACCEPTED, TaskState.REJECTED},
            TaskState.ACCEPTED: {TaskState.ACCEPTED, TaskState.COMPLETED, TaskState.FAILED},
        }
        if new_state not in allowed.get(workflow.state, set()):
            raise ProtocolStateError(
                f"Invalid task transition {workflow.state.value} -> {new_state.value}"
            )
        workflow.state = new_state
        workflow.updates.put_nowait(acknowledgement)
        return workflow

    def handle_alert_ack(self, acknowledgement: AlertAck) -> AlertWorkflow:
        workflow = self.alerts.get(acknowledgement.alert_id)
        if workflow is None:
            raise UnexpectedAcknowledgementError(
                f"No tracked alert matches {acknowledgement.alert_id}"
            )
        states = {
            AlertAck.ALERT_ACK_STATUS_ACCEPTED: AlertState.ACCEPTED,
            AlertAck.ALERT_ACK_STATUS_REJECTED: AlertState.REJECTED,
            AlertAck.ALERT_ACK_STATUS_CANCELLED: AlertState.CANCELLED,
        }
        if workflow.state is not AlertState.PENDING:
            raise ProtocolStateError(f"Alert {workflow.alert_id} is already resolved")
        workflow.state = states[acknowledgement.alert_ack_status]
        workflow.updates.put_nowait(acknowledgement)
        return workflow
