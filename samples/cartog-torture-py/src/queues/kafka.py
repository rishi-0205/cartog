"""Kafka — producer.send and consumer loop. PATTERN: MQ-KAFKA-01."""
from kafka import KafkaProducer, KafkaConsumer

producer = KafkaProducer()

async def send_kafka(topic: str, data: object) -> None:
    """Send to a Kafka topic."""
    producer.send(topic, value=str(data))

def consume(topic: str):
    """Iterate messages from a topic."""
    c = KafkaConsumer(topic)
    return c
