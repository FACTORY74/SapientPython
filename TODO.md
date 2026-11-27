# SAPIENT Python work backlog

## Direction and boundaries

This project already provides the BSI Flex 335 v2.0 message model, validation,
framing, transports, and basic node lifecycle primitives. It is not yet a
complete or independently validated SAPIENT system.

Build an optional, embeddable node runtime on top of the existing library.
The same runtime can later be hosted as a standalone process with an integration
API. Low-level users must still be able to use messages, codecs, transports, and
endpoints without running a node.

The runtime should automate protocol and connection management, not impose
sensor algorithms, fusion decisions, tasking policy, or real-world actions.
Applications supply those through explicit adapters and policies. A local
integration API is not part of the SAPIENT wire standard.

The following ten steps are ordered by priority. Each includes its intended
outcome; tests and documentation are part of each step, not deferred to the
end.

## 1. Establish the role and conformance baseline

- [ ] Map applicable BSI Flex 335 v2.0 requirements to edge, fusion, and
  transparent message-handler behaviours, marking each as implemented,
  partial, unsupported, or application-owned. Include initialization, message
  directions, tasks, alerts, reconnection, platforms, and hierarchy.
  Correct the claim in `Documentation/validation.md` that lifecycle code
  already enforces all cross-message consistency.

  **Done when:** the matrix cites standard clauses and implementation/tests
  where applicable, and documentation accurately describes present behaviour
  without claiming certification.

## 2. Harden registration and session identity

- [ ] Strengthen managed registration and session state: correlate replies
  with registration attempts, handle registration resend requests, define
  duplicate-node and concurrent-session behaviour, and provide acceptance or
  rejection policy hooks. Enforce session identity, initialization ordering,
  and applicable destination rules; safely close or reset failed initialization.

  **Done when:** tests cover acceptance, rejection, wrong or unexpected peers,
  duplicates, invalid ordering, and reconnecting registered nodes, while
  preserving low-level APIs.

## 3. Supervise connection and status lifecycles

- [ ] Add an opt-in supervised receive loop that detects disconnection,
  reconnects with configurable limits and cancellation, and applies the
  standard's re-registration timing. Provide periodic status and configurable
  liveness monitoring, including the applicable registered status interval
  rules. Define shutdown and failed `GOODBYE` behaviour; expose frame-size and
  connection-monitoring configuration.

  **Done when:** tests exercise timeouts, short and long outages, status
  scheduling, liveness transitions, cancellation, and failed shutdown without
  requiring applications to drive recovery manually.

## 4. Enforce stateful, role-aware protocol rules

- [ ] Validate messages against registered state where the standard requires
  it: roles and message flows, declared capabilities, modes, status categories
  and intervals, coordinate systems and datum, and target task support.
  Handle platform/dependent-node declarations. Separate normative checks from
  configurable deployment policy and make violations observable.

  **Done when:** focused tests demonstrate both valid flows and rejection of
  inconsistent messages, and the documentation identifies checks that remain
  application-owned or unsupported.

## 5. Provide edge-node behaviour adapters

- [ ] Define an embeddable edge runtime with sensor and effector adapters:
  publish status, detections and alerts; receive tasks and alert responses;
  invoke application handlers; and send appropriate acknowledgements. Support
  applicable default-task, override, and command-completion behaviour without
  implementing device-specific actions or assuming every node is taskable.

  **Done when:** a simulated sensor and effector demonstrate registration,
  reporting, task acceptance or rejection, execution callbacks and completion,
  including handler failures and shutdown.

## 6. Provide fusion-node workflows and extension points

- [ ] Build an embeddable fusion runtime that maintains a node registry,
  dispatches reports and alerts, sends addressed tasks and alert responses, and
  correlates acknowledgements. Provide explicit hooks for fusion, task
  selection, approval, and registration policy; do not make operational
  decisions or fuse tracks by default. Keep transparent routing separate from
  fusion behaviour.

  **Done when:** tests and an example show multiple edge nodes registering,
  producing reports, receiving an application-selected task, and reporting its
  outcome, including an alert response and observable failures.

## 7. Add persistence and operational resilience

- [ ] Define storage interfaces for registrations/capabilities, events, and
  workflow state, with a usable reference implementation independent of any
  particular production database. Specify restart recovery, disconnected
  buffering/replay, duplicate handling, retention, capacity and back-pressure.
  Bound error storage and expose persistence failures, structured logs and
  health metrics.

  **Done when:** restart, unavailable storage, full buffers, and replay tests
  demonstrate the documented guarantees; no silent data-loss or durability
  guarantee is implied beyond the selected implementation.

## 8. Support hierarchical fusion nodes

- [ ] Compose a downstream fusion server and an upstream edge-like client in
  one runtime. Allow a child fusion node to register its supported aggregate
  capabilities, publish reports and coverage changes, and receive parent
  tasks. Delegate aggregation and downstream task decisions to application
  policy; account for platform relationships where applicable.

  **Done when:** a parent/child/edge integration test covers registration,
  reporting, task and acknowledgement flow, and connection loss on either
  side without assuming a fixed hierarchy depth.

## 9. Offer an optional process and integration API

- [ ] Host the same embeddable runtime as a configurable standalone service.
  Provide an application-facing API to inspect nodes, capabilities, health,
  recent events and workflow state, subscribe to updates, and submit permitted
  tasks or alert responses. Define authentication, authorization, audit,
  operator approval and transport-security boundaries before exposing control
  operations. Keep this API distinct from the SAPIENT wire interface.

  **Done when:** an example starts and stops the service, queries and subscribes
  to state, and submits an authorized task; tests cover rejected access and
  failed operations. Existing applications can still embed the runtime.

  A Kody adapter remains a separate integration application. Its manifest,
  persistent operational picture, track association/history, coordinate
  conversion, GeoJSON projection and operator workspace are Kody-specific;
  live detections should enter through the same event pipeline rather than
  creating tracks directly through REST.

## 10. Verify interoperability and release readiness

- [ ] Complete the clause-to-test matrix and publish supported and unsupported
  requirements. Test independent golden payloads and an independent SAPIENT
  peer; record peer version, transport and results. Add malformed/adversarial
  peer, framing and validation property tests, real-certificate TLS tests,
  resource limits, and clean Windows/Linux package-install checks.

  **Done when:** a reproducible conformance-oriented report distinguishes
  internal tests from independent interoperability evidence, packaging and
  deployment are verified, and release claims match the verified scope. Do not
  claim full conformance solely because the internal suite passes.
