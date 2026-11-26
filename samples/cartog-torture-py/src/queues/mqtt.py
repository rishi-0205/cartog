"""MQTT — publish to topic. PATTERN: MQ-MQTT-01."""
def publish_mqtt(topic: str, payload: str) -> None:
    """Publish an MQTT message."""
    print(topic, payload)
