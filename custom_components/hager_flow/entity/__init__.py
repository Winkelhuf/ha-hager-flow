"""
Entity package for the Hager flow integration.

Architecture:
    All platform entities inherit from (PlatformEntity, HagerFlowEntity).
    MRO order matters — platform-specific class first, then the integration base.
    Entities read data from coordinator.data and NEVER call the API client directly.
    Unique IDs follow the pattern: {entry_id}_{description.key}

See entity/base.py for the HagerFlowEntity base class.
"""

from .base import HagerFlowEntity

__all__ = ["HagerFlowEntity"]