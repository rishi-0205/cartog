"""RabbitMQ/AMQP — basic_publish/basic_consume. PATTERN: MQ-RABBITMQ-01."""
import pika

connection = pika.BlockingConnection()
channel = connection.channel()

def basic_publish(queue: str, body: object) -> None:
    """Publish to a queue."""
    channel.basic_publish(exchange="", routing_key=queue, body=str(body))

def basic_consume(queue: str, cb) -> None:
    """Register a consumer callback."""
    channel.basic_consume(queue=queue, on_message_callback=cb)

def on_msg(ch, method, props, body):
    """Handle a consumed message."""
    return None
