// PATTERN: TRAP-LOCAL-CLASS-01 — local class used as broker
export class EventBus { add(x: unknown): void { return; } }
const bus = new EventBus("bus-name");
bus.add({});
