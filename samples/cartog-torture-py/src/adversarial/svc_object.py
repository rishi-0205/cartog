"""Object-literal service container reached through wildcard barrel."""
def handle(data):
    """Handle data through an internal validator."""
    return validate_data(data)

def validate_data(d):
    """Validate the data."""
    return d
