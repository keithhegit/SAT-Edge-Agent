from __future__ import annotations

import sys

from backend.services import detection_service as _backend_detection_service


sys.modules[__name__] = _backend_detection_service
