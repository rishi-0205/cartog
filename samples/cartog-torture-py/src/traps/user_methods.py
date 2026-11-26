# PATTERN: TRAP-USER-PUBLISH-01 — ordinary publish() no channel context
def publish(x): pass
publish("hello")
