# SAPIENT interface examples

## Role-oriented deployment example

The [`roles/`](roles/README.md) example represents a complete small deployment
with separate sensor, C2/fusion, and effector processes. It shows registration,
initial status, detections, tasking, acknowledgements, and graceful sensor
shutdown. Start here when learning which participant sends each message.

The remaining files are smaller examples focused on one API or workflow.

Run examples from an activated project environment, for example:

```powershell
python examples/messages.py
python examples/registration_flow.py
python examples/task_workflow.py
```

- `messages.py` constructs and validates representative outer messages.
- `fusion_server.py` starts a managed fusion-node server.
- `edge_node.py` shows edge-node connection and initialization.
- `registration_flow.py` runs both roles locally and demonstrates registration and graceful shutdown.
- `task_workflow.py` demonstrates correlated task acknowledgements.
- `custom_transport.py` shows the small transport interface required by senders and receivers.
- `roles/c2_node.py` runs a C2/fusion receiver and task sender.
- `roles/sensor_node.py` registers a sensor and publishes observations.
- `roles/effector_node.py` receives a task and reports acceptance and completion.

The examples use loopback addresses and synthetic identifiers. Replace these values and message capabilities with deployment-specific configuration.
