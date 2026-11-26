# PATTERN: TRAP-LOCAL-CLASS-01 — local class used as broker
class EventBus:
    def add(self, x): pass
b = EventBus("bus-name")
b.add(1)
