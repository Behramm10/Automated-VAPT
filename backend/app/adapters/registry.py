"""
Adapters Registry — factory for creating target adapters.
"""
from __future__ import annotations
from app.adapters.base import TargetAdapter
from .mock import MockAdapter
from .local_python import LocalPythonAdapter
from .rest import RestAdapter

ADAPTER_REGISTRY: dict[str, type[TargetAdapter]] = {
    "mock": MockAdapter,
    "local_python": LocalPythonAdapter,
    "rest": RestAdapter,
}

def register_adapter(name: str, cls: type) -> None:
    ADAPTER_REGISTRY[name] = cls

def create_adapter(adapter_type: str, **kwargs) -> TargetAdapter | None:
    cls = ADAPTER_REGISTRY.get(adapter_type)
    if cls:
        return cls(**kwargs)
    return None
