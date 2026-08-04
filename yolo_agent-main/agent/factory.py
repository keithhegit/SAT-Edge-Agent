from __future__ import annotations

import sys

from backend.agent import factory as _backend_factory


sys.modules[__name__] = _backend_factory
