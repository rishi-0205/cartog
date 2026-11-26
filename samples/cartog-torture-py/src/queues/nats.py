"""NATS — publish to subject. PATTERN: MQ-NATS-01."""
def publish_nats(subject: str, data: object) -> None:
    """Publish to a NATS subject."""
    print(subject, data)
