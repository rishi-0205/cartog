"""Azure Service Bus — send. PATTERN: MQ-AZURE-01."""
def send_azure(queue: str, data: object) -> None:
    """Send to an Azure queue."""
    print(queue, data)
