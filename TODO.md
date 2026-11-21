# SAPIENT Python work backlog

## Current assessment

This project is a substantial BSI Flex 335 v2.0 messaging library and reference
integration framework. It provides the complete v2.0 protobuf wire model,
message construction, validation, serialization, stream framing, TCP/TLS,
basic node lifecycles, acknowledgement tracking, and transparent routing.

It is not yet a complete or independently validated SAPIENT system. Passing the
internal test suite demonstrates that the library is internally consistent; it
does not establish interoperability or BSI conformance.

## System boundary

### This repository: protocol and connection library

The `sapient-interface` package owns the SAPIENT protocol boundary:

- v2.0 message types and message construction;
- structural and context-free semantic validation;
- protobuf encoding and decoding;
- byte-stream framing;
- TCP/TLS and custom transport abstractions;
- connection/session lifecycle primitives;
- registration and acknowledgement correlation;
- optional routing and persistence callbacks.

It does **not** own a persistent operational picture. In particular, this
package should not decide that detections represent the same long-lived track,
perform track fusion, retain track history, expose a track-management REST API,
or publish map features. Those responsibilities require application policy and
belong above the protocol library.

The library may retain limited protocol state needed to enforce a live session,
such as the registered node identity, declared capabilities, selected coordinate
systems, active tasks, acknowledgement state, and last status time. Durable
storage should be supplied through an interface rather than embedded as a
particular database.

### Kody SAPIENT service: persistent integration application

A future Kody adapter should be a separately deployable Kody microservice that
uses this library. It should own the longer-lived operational state:

- persistent node registrations and connection history;
- the raw SAPIENT message/event journal;
- detection-to-track association and track identity policy;
- current track state and bounded track history;
- coordinate conversion into WGS 84 longitude/latitude;
- stale-track, expiry, merge, split, and deletion policy;
- GeoJSON projection for Kody's `dataLayer` contract;
- REST/workspace APIs for connections, tracks, tasks, and alerts;
- outgoing task/alert workflows and their acknowledgement state;
- restart recovery and, where appropriate, message replay.

The service should consume both externally assigned `object_id` values and
fusion-node detections without assuming that every detection is automatically a
new track. Track aggregation must be an explicit policy layer with provenance:
each track should retain the contributing node/detection identifiers.

The normal data flow should be event-driven rather than creating tracks through
REST calls:

```text
SAPIENT Registration/Status/Detection/Alert messages
                         |
                         v
             Kody SAPIENT integration service
             |-- durable event journal
             |-- node/session registry
             |-- track aggregation and history
             |-- task/alert workflows
             `-- WGS 84 GeoJSON projection
                         |
                         v
                    Kody map
```

REST API calls should configure the service, query tracks/history, correct or
annotate tracks, and initiate operator tasks. They should not normally be the
primary mechanism for creating live tracks. A simulation/test endpoint may
inject synthetic detections, but should feed them through the same ingestion
pipeline as network messages.

## Protocol conformance work

### Registration and identity

- [ ] Correlate an acknowledgement with the active registration attempt.
- [ ] Support a fusion node requesting registration to be resent.
- [ ] Add registration policy callbacks so a managed fusion server can reject
  unsupported, duplicate, unauthorized, incompatible, or over-capacity nodes.
- [ ] Define and test duplicate-node and concurrent-session behavior.

### Connection lifecycle

- [ ] Add a supervised receive loop that detects connection loss and invokes
  configurable reconnection automatically.
- [ ] Preserve the two-minute re-registration rule while making recovery
  automatic rather than application-triggered.
- [ ] Ensure failed initialization closes or safely resets its connection.
- [ ] Add keepalive/connection-monitoring configuration appropriate to deployed
  TCP environments.
- [ ] Make maximum message size configurable through edge and fusion role APIs.
- [ ] Test TLS client and server operation with real certificates, hostname
  verification, rejection cases, and reconnects.
- [ ] Define shutdown behavior when sending `SYSTEM_GOODBYE` itself fails.

### Stateful protocol enforcement

- [ ] Enforce that all messages on a registered session use the registered
  `node_id` and valid destination rules.
- [ ] Check later location values against the coordinate systems and datum
  declared during registration.
- [ ] Check status categories, units, and intervals against the registration.
- [ ] Check detection classifications and modes against declared capabilities.
- [ ] Check tasks against the commands, regions, modes, and coordinate systems
  declared by the target node.
- [ ] Track the last status time and expose a configurable offline/liveness
  decision, including the registered three-interval rule.
- [ ] Provide a regular status scheduler/helper for edge-node applications.
- [ ] Implement platform/dependent-node consistency checks.
- [ ] Implement or explicitly scope out hierarchical fusion-node coordination.
- [ ] Reconcile the validation documentation with the checks actually enforced
  by the lifecycle layer.

### Persistence and operations

- [ ] Define storage protocols for registered-node state, messages/events, and
  workflow state without coupling the library to one database.
- [ ] Restore appropriate registration and workflow state after restart.
- [ ] Define buffering/replay behavior during disconnection.
- [ ] Add bounded retention and back-pressure behavior.
- [ ] Replace or bound the fusion server's unbounded in-memory error list.
- [ ] Add structured logging and operational metrics.
- [ ] Ensure persistence failures are observable and cannot silently lose data.

### Validation coverage

- [ ] Build a requirement-to-code/test traceability matrix for every normative
  `shall` in BSI Flex 335 v2.0 that applies to the software boundary.
- [ ] Review every schema field and textual semantic constraint, not only the
  currently selected rules.
- [ ] Add boundary and invalid-value tests for every coordinate system, datum,
  range/bearing unit, enumeration, timestamp, and identifier field.
- [ ] Validate cross-field defaults and conditional fields described in the
  standard.
- [ ] Test maximum-size messages and resource-exhaustion cases.
- [ ] Add fuzz/property tests for framing, protobuf decoding, and validation.
- [ ] Add malformed and adversarial peer tests.

### Interoperability and release readiness

- [ ] Obtain or create independent golden protobuf payloads for every outer
  message type and representative inner-message combinations.
- [ ] Test against at least one independent SAPIENT peer implementation.
- [ ] Capture interoperability results, peer version, transport, and test cases.
- [ ] Add a conformance test report distinct from ordinary unit-test coverage.
- [ ] Add Windows and Linux CI with clean package installation.
- [ ] Test source distribution and wheel installation in isolated environments.
- [ ] Document supported versus unsupported standard clauses.
- [ ] Do not describe the package as fully conformant until the traceability and
  independent interoperability work is complete.
- [ ] Promote from alpha only after the public API and lifecycle behavior are
  stable.

## Kody integration plan

The adapter should follow Kody's independent-microservice boundary and expose
`GET /api/kody/manifest`. It should not add SAPIENT-specific logic to the Kody
core.

### Phase 1: read-only situational picture

- [ ] Create a standalone `sapient` Kody service using Python 3.15.
- [ ] Add this package and `protobuf` to Kody's offline wheel bundle.
- [ ] Accept configured SAPIENT TCP/TLS connections.
- [ ] Persist registrations, statuses, detections, alerts, errors, and raw
  envelopes with receipt timestamps.
- [ ] Maintain node connection and liveness state.
- [ ] Convert WGS 84 Cartesian detections to GeoJSON features.
- [ ] Preserve source node, object, report, classification, confidence, and
  timestamp provenance in GeoJSON properties.
- [ ] Implement the Kody `dataLayer` manifest and revision behavior.
- [ ] Provide configuration and health endpoints.
- [ ] Provide a workspace showing connections, registered capabilities, errors,
  and recent messages.

### Phase 2: coordinate and track processing

- [ ] Convert UTM locations to WGS 84.
- [ ] Convert range/bearing detections using the reporting node's known location
  and declared datum.
- [ ] Define identity rules for node `object_id`, fused detections, and associated
  detections.
- [ ] Implement persistent current-track state and bounded history.
- [ ] Define stale, expired, merged, split, and manually corrected track states.
- [ ] Retain raw observations separately from derived track state.
- [ ] Make aggregation policy configurable and testable.
- [ ] Publish track trails and source/provenance information to Kody.

### Phase 3: bidirectional operation

- [ ] Add APIs and workspace actions for creating and sending SAPIENT tasks.
- [ ] Allow a selected Kody feature or drawn region to populate task geometry.
- [ ] Transform outgoing task coordinates into the target node's registered
  coordinate system.
- [ ] Display task acknowledgement transitions and completion/failure reasons.
- [ ] Display and acknowledge alerts.
- [ ] Recover unfinished task/alert workflows after restart.
- [ ] Add authorization and audit records for operator-generated commands.

### Phase 4: deployment hardening

- [ ] Add TLS certificate and trust-store configuration without storing secrets
  in ordinary Kody configuration responses.
- [ ] Add retention, capacity, and back-pressure controls.
- [ ] Add service metrics, structured logs, and readiness/liveness endpoints.
- [ ] Test restart, network partition, delayed messages, duplicates, and
  out-of-order delivery.
- [ ] Run end-to-end tests using an independent SAPIENT producer and Kody.
- [ ] Document offline installation, ports, storage locations, backup, and
  recovery.

## Definition of done

The protocol package may be described as a full implementation only when:

1. every applicable normative requirement is mapped to implementation and an
   automated or documented verification;
2. registration, connection loss, liveness, state consistency, and hierarchy
   are implemented or explicitly declared outside the supported boundary;
3. the library interoperates with an independent SAPIENT implementation;
4. supported and unsupported clauses are published; and
5. release packaging and clean deployment are verified on supported platforms.
