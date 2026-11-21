# SAPIENT Python Interface Architecture

## 1. Purpose

This repository provides a reusable Python 3.15 interface for SAPIENT systems conforming to BSI Flex 335 v2.0. It separates the standard message model from message framing, networking, and application roles so the library can be embedded in sensor, effector, fusion, middleware, test, and simulation projects.

The official Protocol Buffer files under `Documentation/` remain the normative source for the wire format. Copies are packaged under `src/sapient_msg/` and their generated Python modules are committed so users do not need `protoc` at runtime.

## 2. Design principles

- **Standards first:** the BSI Flex 335 v2.0 protobuf schema defines the serialized representation.
- **Stable public API:** consumers import from `sapient`, not generated protobuf internals.
- **Separation of concerns:** messages, validation, framing, transports, endpoints, and node roles are independent layers.
- **Transport independence:** TCP is the first transport, but endpoints depend on a small connection protocol.
- **Transparent handling:** relays and message handlers do not alter message content.
- **Fail safely:** frame sizes, mandatory fields, UUIDs, ULIDs, and mandatory one-of selections are validated.
- **Integration friendly:** applications may use the whole node-role layer or only messages and codecs.

## 3. Protocol model

Every wire message is a `SapientMessage` envelope containing:

- the UTC time associated with the content;
- the sender's UUID in `node_id`;
- an optional destination UUID;
- exactly one of registration, registration acknowledgement, status report, detection report, task, task acknowledgement, alert, alert acknowledgement, or error;
- optional additional information.

On a continuous byte stream, the serialized protobuf message is prefixed by a four-byte unsigned little-endian length. The prefix does not include its own four bytes.

The normal initialization sequence is registration, registration acknowledgement, then initial status. Edge nodes are normally clients. A fusion node or a separate transparent message handler normally accepts their connections.

## 4. Layering

```text
Application / project integration
             |
       roles (optional)
             |
   sender and receiver endpoints
             |
      codec and validation
             |
     transport connection
             |
 TCP byte stream (initial implementation)
```

Applications that already own their networking can use `sapient.codec` directly. Applications that already own their lifecycle can use `SapientSender` and `SapientReceiver`. Complete nodes can use the role classes.

## 5. Repository organization

```text
Sapient/
|-- architecture.md             This document
|-- requirements.txt            Runtime and test dependencies
|-- pyproject.toml              Package metadata and build configuration
|-- setup_env.cmd               Windows launcher (handles execution policy)
|-- setup_env.ps1               Windows environment setup and verification
|-- setup_env.sh                POSIX environment setup and verification
|-- Documentation/              Standards, reference material, and original schemas
|-- examples/                   Runnable API and role-oriented examples
|   `-- roles/                  Separate sensor, C2, and effector processes
|-- scripts/
|   |-- generate_protos.py       Rebuilds Python modules from the .proto schemas
|   |-- quick_test.py            Fast serialization and loopback TCP harness
|   `-- test_report.py           Optional one-line-per-test report plugin
|-- src/
|   |-- sapient/                 Stable, hand-written public API
|   |   |-- messages/            Envelope helpers and message exports
|   |   |-- codec/               Protobuf encoding and stream framing
|   |   |-- validation/          Standards-aware validation
|   |   |-- transports/          Abstract connection and TCP implementation
|   |   |-- endpoints/           Generic message sender and receiver
|   |   |-- roles/               Edge/fusion/message-handler behavior
|   |   `-- errors.py            Public exception hierarchy
|   |-- sapient_msg/             Packaged schemas and generated protobuf code
|   `-- sapient_interface.egg-info/  Generated installation metadata (ignored)
`-- tests/                       Automated unit and integration tests
```

The repository uses the standard Python `src` layout: importable packages live
under `src/` rather than beside the project configuration. `sapient/` is the API
application code should import. `sapient_msg/` is the lower-level generated wire
format used internally by that API. `tests/` verifies both layers, while
`examples/` demonstrates typical application usage. `scripts/` contains
development and verification utilities rather than library code.

### Generated and working folders

Some folders may appear after installing or testing the project but are not part
of its authored source code:

- `src/sapient_interface.egg-info/` is package metadata generated by an editable
  install such as `pip install -e .` or `uv pip install -e .`. Its files record
  the distribution name, version, dependencies, packaged sources, and top-level
  import packages. The distribution is named `sapient-interface`, hence the
  underscore-normalized folder name. It can be safely deleted; the next install
  recreates it. It is excluded from Git by `*.egg-info/`.
- `.venv/` is the local Python virtual environment containing the interpreter and
  installed dependencies. It is machine-specific, ignored by Git, and should be
  recreated rather than copied between project locations.
- `.pytest_cache/`, `__pycache__/`, and `.coverage` are generated test, bytecode,
  and coverage caches. They are disposable and ignored by Git.
- `tmp/`, `build/`, and `dist/` hold temporary or packaging output. They are also
  generated, disposable, and ignored by Git.

Deleting these generated folders does not delete the implementation. The authored
packages are `src/sapient/` and `src/sapient_msg/`.

### `sapient.messages`

Defines the public message surface. `create_message()` constructs a correctly timestamped envelope and inserts any supported outer payload. Modules such as `registration`, `status`, and `task` expose the generated types without requiring callers to know their generated module paths.

### `sapient.codec`

Converts envelopes to and from protobuf bytes and implements BSI's four-byte little-endian framing. `FrameDecoder` supports fragmented and coalesced reads, which are normal properties of TCP.

### `sapient.validation`

Interprets the validation annotations embedded in the supplied protobuf descriptors. It checks mandatory scalar/message/repeated fields, mandatory one-of groups, UUID fields, ULID fields, and recursively nested messages. Validation occurs before encoding and after decoding by default.

### `sapient.transports`

Contains the minimal `MessageConnection` protocol and the initial asyncio TCP implementation. The TCP connection applies the frame-length limit before allocating or reading a payload. A future TLS, serial, WebSocket, or in-memory transport can implement the same protocol.

### `sapient.endpoints`

`SapientSender` and `SapientReceiver` operate on a connection. They only handle complete `SapientMessage` envelopes and do not contain business logic for particular payloads.

### `sapient.roles`

Provides complete convenience lifecycle objects. `EdgeNode` performs registration, initial status, configurable reconnection, and graceful `GOODBYE`. `FusionNodeServer` accepts concurrent clients, optionally manages registration state, and delegates operational messages to an application callback. `AcknowledgementTracker` correlates task and alert transitions. `TransparentMessageHandler` routes unchanged envelopes by destination.

### `sapient_msg`

Contains copied official `.proto` sources and generated `_pb2.py` files. It is an implementation detail. Regeneration requires `grpcio-tools`, but normal installation and execution require only `protobuf`.

## 6. Dependency policy

The runtime depends on Google's `protobuf` package because BSI Flex 335 mandates Protocol Buffers. Networking, concurrency, identifiers, and framing use the Python 3.15 standard library. `pytest` is a development/test dependency included in `requirements.txt` so a newly created environment can immediately validate the repository.

## 7. Error handling and limits

All public failures derive from `SapientError`:

- `ValidationError` for invalid message content;
- `CodecError` for malformed protobuf data;
- `FramingError` for invalid or oversized frames;
- `ConnectionClosedError` for an incomplete or closed stream.

TCP connections default to a 16 MiB maximum message size. Integrators may lower or raise this explicitly, but receivers always reject a declared frame larger than their configured limit.

## 8. Test strategy

`scripts/quick_test.py` is the fast operational harness. It validates:

1. construction and standards-aware validation of a status envelope;
2. protobuf serialization and deserialization;
3. length-prefix framing, including fragmented input;
4. a real asyncio TCP loopback exchange.

`pytest` covers the same components independently and includes negative cases. Both setup scripts create a Python 3.15 virtual environment, install the package and dependencies, run the quick harness, and run the test suite.

On Windows, run `setup_env.cmd`; it launches the PowerShell setup with a process-scoped execution-policy bypass and does not change the user's machine policy. On macOS or Linux, run `sh setup_env.sh`.

## 9. Versioning and future work

The initial API intentionally supports only BSI Flex 335 v2.0. Future standard versions should live in separate generated namespaces and be selected explicitly at a compatibility boundary. They must not silently change v2.0 behavior.

Releases use semantic versioning. Until version 1.0, minor releases may refine the public API while patch releases remain backwards compatible. Regenerate committed protobuf modules with `python scripts/generate_protos.py`; verify them without changing files with `python scripts/generate_protos.py --check`. The generator is pinned in `requirements.txt`.

TLS, reconnection timing, registration state, acknowledgement workflows, and transparent routing are implemented above the message layer. Future extensions can add application-framework adapters and deployment-specific persistence while preserving these boundaries.
