# Sensor, C2, and effector example

These three processes demonstrate the roles in a small SAPIENT deployment:

```text
Sensor                              C2 / fusion node                      Effector
  |                                       |                                  |
  |--- Registration --------------------->|<---------------- Registration ---|
  |<-- RegistrationAck -------------------|--------------- RegistrationAck ->|
  |--- initial StatusReport ------------->|<-------------- initial Status ---|
  |                                       |                                  |
  |--- DetectionReport ------------------>|                                  |
  |                                       |--------------- Task ------------>|
  |                                       |<-------------- TaskAck accepted -|
  |                                       |<-------------- TaskAck complete -|
  |--- SYSTEM_GOODBYE ------------------->|                                  |
```

The sensor sends three positions with one stable, source-local `object_id`.
This demonstrates observation continuity; the messaging library does not turn
those observations into a durable or fused track. A C2/Kody integration service
would own that longer-lived aggregation policy.

## Run the example

Activate the project environment and open three terminals at the repository
root. Start the roles in this order:

```powershell
# Terminal 1: server and task originator
python -m examples.roles.c2_node

# Terminal 2: task recipient
python -m examples.roles.effector_node

# Terminal 3: observation producer
python -m examples.roles.sensor_node
```

The C2 node accepts both registrations, prints the sensor observations, sends
one task to the effector, and prints the accepted/completed task transitions.
The identifiers, loopback address, timing, and actions are deliberately fixed
to keep the message flow easy to follow.

These are role demonstrations, not a persistent C2 product. They do not store
messages or tracks, authenticate nodes, or recover state after restart.
