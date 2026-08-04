from __future__ import annotations

import sys

from backend.utils import message_utils as _backend_message_utils


sys.modules[__name__] = _backend_message_utils
