"""Route registration with callback kwarg."""
def register(server, callback):
    """Register a handler with a callback kwarg."""
    server.on("connection", on_message_callback=callback)

def on_message_callback(msg):
    """Handle a message."""
    return msg
