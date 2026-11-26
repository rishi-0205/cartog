"""AWS SQS — send_message with QueueUrl kwarg. PATTERN: MQ-SQS-01."""
import boto3

sqs = boto3.client("sqs")

def send_sqs(body: str) -> None:
    """Send an SQS message."""
    sqs.send_message(QueueUrl="http://q", MessageBody=body)
