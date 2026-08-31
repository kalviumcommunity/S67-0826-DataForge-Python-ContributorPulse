"""
Legacy compatibility package for database models.

Re-exports domain models from backend.app.models for backward compatibility.
New code should import directly from backend.app.models.
"""

from backend.app.models import *  # noqa: F401, F403
