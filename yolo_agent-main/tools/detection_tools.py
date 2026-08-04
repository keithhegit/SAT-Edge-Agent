from __future__ import annotations

import sys

from backend.tools import detection_tools as _backend_detection_tools


sys.modules[__name__] = _backend_detection_tools
