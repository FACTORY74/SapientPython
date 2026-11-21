# Integration guide

## Installation

On Windows, run `setup_env.cmd`. On macOS or Linux, run `sh setup_env.sh`. Both create a Python 3.15 virtual environment, install runtime and verification dependencies, run the quick harness, and execute the complete test suite.

Set `SAPIENT_VENV` to use a different environment directory. This is useful for clean-checkout verification and CI; repeated runs reuse and refresh the selected environment.

Runtime consumers can install the project as a normal Python package. Only `protobuf` is required at runtime; generator, build, coverage, and test tools are development dependencies listed in `requirements.txt`.

## Choosing an integration layer

- Use `sapient.messages`, `sapient.validation`, and `sapient.codec` when an application already owns its byte transport.
- Use `SapientSender` and `SapientReceiver` when an application owns connection lifecycle but wants complete-envelope I/O.
- Use `EdgeNode` or `FusionNodeServer` for the standard connection and registration lifecycle.
- Use `TransparentMessageHandler` to route envelopes between connected nodes by `destination_id` without changing their content.

## Edge-node lifecycle

Create an `EdgeNode` with its UUID and call `initialize(registration, initial_status)`. The node sends registration, requires an accepted registration acknowledgement addressed to its own UUID, and sends initial status before entering `INITIALIZED`. The default response timeout is 30 seconds. On timeout it closes the connection, reconnects, and resends registration once by default; configure `max_attempts` when a different bound is needed. Pass `expected_fusion_node_id` to `EdgeNode.connect()` when the peer UUID is known and must be verified. An SAPIENT error received instead of an acknowledgement ends initialization with `ProtocolStateError`. `close()` sends a `SYSTEM_GOODBYE` status by default.

`reconnect()` retries at a configurable interval (10 seconds by default). It preserves registration during outages shorter than the configurable threshold (120 seconds by default) and performs registration again after longer outages. `max_attempts` and `cancel_event` let embedding applications bound or cancel recovery.

## Fusion-node lifecycle

Start `FusionNodeServer` with `manage_registrations=True` and a fusion-node UUID. It validates incoming messages, acknowledges registrations, retains registration/capability content, marks nodes online/offline, rejects operational messages from unknown nodes, and closes active sessions during bounded shutdown.

The application handler receives operational messages and a sender for replies. Handler and decoding failures are available in `server.errors` and may also be delivered immediately through `error_handler`.

## Task and alert correlation

`AcknowledgementTracker` creates task and alert workflows keyed by ULID. It validates acknowledgement correlation and legal state transitions. Each workflow exposes an asynchronous `wait(timeout=...)` queue for updates.

## Transparent routing

Register each connected node's `SapientSender` with `TransparentMessageHandler`. Registration messages without a destination go to the configured fusion node; other messages use `destination_id`. Unknown destinations raise `UnknownDestinationError` after an optional callback. An optional persistence hook observes each original envelope without coupling storage to routing.

## TLS and custom transports

Pass an `ssl.SSLContext` to `EdgeNode.connect`, `open_tcp_connection`, or `FusionNodeServer.start` to secure TCP. For a different transport, implement three asynchronous methods: `send_payload(bytes)`, `receive_payload() -> bytes`, and `close()`. No inheritance is required.

## Validation scope

See `Documentation/validation.md` for implemented structural and semantic checks. Consistency that depends on deployment policy or historical messages can be added above the validation layer using registered-node state.
