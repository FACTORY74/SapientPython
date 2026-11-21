# Implemented BSI Flex 335 validation

The validator applies the custom mandatory, UUID, ULID, and mandatory-oneof annotations from the supplied v2.0 protobuf descriptors. It also implements semantic constraints stated in BSI Flex 335 v2.0 that are not represented by those annotations.

Implemented semantic checks:

- UUID fields must contain UUID version 4 values;
- mandatory enumerations cannot use their zero/`UNSPECIFIED` value;
- protobuf timestamps must be representable within the protobuf timestamp range;
- task end time cannot precede task start time;
- a predicted detection timestamp must be later than its containing detection timestamp;
- detection, classification, subclass, behaviour, and alert confidence/ranking values are in the inclusive range 0 to 1;
- reported battery percentage is in the inclusive range 0 to 100;
- a task contains at least one region or command;
- Cartesian location latitude/longitude values respect degree or radian bounds;
- UTM zone fields are used only with UTM coordinate systems;
- registration location coordinate and datum alternatives are paired consistently;
- predicted locations select either Cartesian or range-bearing coordinates;
- rejected registrations contain a reason;
- rejected or failed task acknowledgements contain a reason;
- rejected alert acknowledgements contain a reason;
- detection classification and subclass names use `<namespace>:<value>`;
- subclass levels are non-negative.

System-level consistency between a node's registration and all later locations, capabilities, modes, tasks, and reports is enforced by the lifecycle layer because it requires state from more than one message.
