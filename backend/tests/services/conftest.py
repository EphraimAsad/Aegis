"""Fixtures for service tests.

Mocks external dependencies so service tests can run without Redis/DB.
"""

import sys
from unittest.mock import MagicMock

# Mock modules that require external dependencies
# These need to be mocked before any app imports
sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()
