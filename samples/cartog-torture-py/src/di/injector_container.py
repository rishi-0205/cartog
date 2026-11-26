"""dependency_injector — service locator. PATTERN: DI-CONSTRUCTOR-01."""
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    """DI container."""
    service = providers.Factory(object)

def container_get(name: str) -> object:
    """Resolve a service from the container."""
    return Container.service()
