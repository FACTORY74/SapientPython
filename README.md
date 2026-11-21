# SAPIENT Python Interface

[![Python 3.15](https://img.shields.io/badge/Python-3.15-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

A reusable Python interface for building SAPIENT edge nodes, fusion nodes, message handlers, simulations, and integration tests using **BSI Flex 335 v2.0**.

The project packages the official Protocol Buffer schemas behind a stable Python API and supplies message validation, BSI stream framing, asynchronous TCP transport, node lifecycles, acknowledgement tracking, transparent routing, TLS support, and an end-to-end test harness.

> This is an independent implementation. It is not an official BSI or UK Government product, and using it does not by itself certify a system as conformant.

## Features

- All nine BSI Flex 335 v2.0 outer message types.
- Committed generated protobuf modules—`protoc` is not required at runtime.
- Structural and semantic validation for UUIDs, ULIDs, mandatory fields, enumerations, timestamps, confidence values, coordinates, tasks, and acknowledgements.
- Required four-byte little-endian stream framing.
- Async TCP clients and concurrent servers with optional TLS.
- Edge-node registration, initial status, reconnection, re-registration, and graceful `GOODBYE`.
- Fusion-node registration state and bounded session shutdown.
- Task and alert acknowledgement correlation.
- Transparent routing by `destination_id` with optional persistence hooks.
- Custom transport support through a small protocol-based interface.
- Reproducible protobuf generation and package-content checks.

## Requirements

- Python 3.15 or newer.
- The `protobuf` runtime.
- [`uv`](https://docs.astral.sh/uv/) is recommended for development setup; the supplied scripts install it when necessary.

## Quick start

Clone the repository and run the setup script for your platform.

Windows:

```powershell
setup_env.cmd
```

macOS or Linux:

```sh
sh setup_env.sh
```

The script creates `.venv`, installs the project and verification dependencies, runs the quick TCP harness, and executes the complete test suite.

Activate the environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS and Linux:

```sh
. .venv/bin/activate
```

For a normal editable installation without running the bootstrap script:

```sh
python -m pip install -e .
```

## Constructing a message

Applications import from `sapient`, not from the generated `sapient_msg` implementation package.

```python
from sapient.codec import decode_message, encode_message
from sapient.messages import StatusReport, create_message, new_ulid

status = StatusReport(
    report_id=new_ulid(),
    system=StatusReport.SYSTEM_OK,
    info=StatusReport.INFO_NEW,
    mode="default",
)

message = create_message(
    sender_id="5ea410b7-9656-4d22-929d-3bad7bf15a21",
    destination_id="c86a7289-1de9-493a-b17d-0c9f9f9838f4",
    content=status,
)

wire_payload = encode_message(message)
restored = decode_message(wire_payload)

print(restored.WhichOneof("content"))  # status_report
```

Encoding validates messages by default. Invalid mandatory fields, identifiers, enumerations, one-of selections, or supported semantic constraints raise `ValidationError`.

## Running an edge node

```python
from sapient.roles import EdgeNode

async with await EdgeNode.connect(
    "127.0.0.1",
    5020,
    node_id=edge_node_id,
) as edge:
    await edge.initialize(registration, initial_status)
    await edge.send(message)
```

Initialization follows the required sequence:

```text
Registration -> RegistrationAck -> initial StatusReport
```

An orderly context-manager exit sends a `SYSTEM_GOODBYE` status. `EdgeNode.reconnect()` supports configurable retry intervals, cancellation, attempt limits, and re-registration after longer outages.

## Running a fusion node

```python
from sapient.roles import FusionNodeServer

async def handle_message(message, sender):
    print(message.node_id, message.WhichOneof("content"))

server = await FusionNodeServer.start(
    "127.0.0.1",
    5020,
    handle_message,
    fusion_node_id=fusion_node_id,
    manage_registrations=True,
)

try:
    await run_application()
finally:
    await server.close()
```

Managed registration validates and acknowledges registrations, retains node capabilities, tracks online state, and prevents unregistered nodes from sending operational messages.

## Architecture

```text
Application
    |
Node roles and transparent routing
    |
Sender / receiver endpoints
    |
Validation and protobuf codec
    |
Framing and transport
    |
TCP or a custom byte transport
```

You can adopt only the layers your application needs:

- `sapient.messages`, `sapient.validation`, and `sapient.codec` for applications with their own transport.
- `SapientSender` and `SapientReceiver` for applications that own connection lifecycle.
- `EdgeNode` and `FusionNodeServer` for complete TCP lifecycle support.
- `TransparentMessageHandler` for middleware and routing.

See [architecture.md](architecture.md) for the complete design and folder responsibilities.

## Testing

Run the fast operational harness:

```sh
python scripts/quick_test.py
```

Run the complete suite with branch-aware coverage:

```sh
python -m pytest
```

To also create a concise, one-line result for every expanded test case:

```powershell
python -m pytest -p scripts.test_report --test-report test-report.txt
```

Each line contains the result, a short unique name, and a brief description. Test
docstrings supply descriptions when present; otherwise the test function name is
converted into readable text.

The suite covers every outer message type, representative complex inner messages, validation failures, framing and transport errors, concurrent clients, registration, reconnection, acknowledgements, graceful shutdown, routing, generated-code reproducibility, and package contents.

## Protobuf regeneration

The generated modules are committed so consumers only need the protobuf runtime. Contributors can regenerate them with the pinned compiler dependency:

```sh
python scripts/generate_protos.py
```

Verify that the documentation schemas, packaged schemas, and generated modules agree without modifying files:

```sh
python scripts/generate_protos.py --check
```

## Documentation

- [Architecture and repository organization](architecture.md)
- [Integration guide](Documentation/integration.md)
- [Implemented validation rules](Documentation/validation.md)
- [Executable examples](examples/README.md)
- [Original protobuf documentation](Documentation/SAPIENT-Proto-Files/Readme.md)

## Project status

The package is currently version `0.1.0` and classified as alpha. The supported protocol target is BSI Flex 335 v2.0. Future standard versions will use explicit, separate generated namespaces rather than silently changing v2.0 behavior.

The project uses semantic versioning. Before version 1.0, minor releases may refine the public API; patch releases remain backwards compatible.

## Licence

Licensed under the [Apache License 2.0](LICENSE). The supplied SAPIENT protobuf files retain their Crown copyright and accompanying licence notice.
