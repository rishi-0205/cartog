"""Google Pub/Sub — publish. PATTERN: MQ-GCP-01."""
def publish_gcp(topic: str, data: object) -> None:
    """Publish to a GCP topic."""
    print(topic, data)
