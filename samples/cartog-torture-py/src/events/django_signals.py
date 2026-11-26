"""Django signals — @receiver. PATTERN: EVENT-DJANGO-01."""
from django.dispatch import receiver, Signal

s = Signal()

@receiver(s)
def on_signal(sender, **kwargs):
    """Handle the signal."""
    return None

def django_send(name, data):
    """Send a Django signal."""
    s.send(sender=None)
