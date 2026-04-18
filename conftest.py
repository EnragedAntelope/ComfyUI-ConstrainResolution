import sys
from unittest.mock import MagicMock

# Mock comfy_api before any project module is imported.
# io.ComfyNode must be a real class so ConstrainResolution can inherit from it.
_comfy_api_latest = MagicMock()
_comfy_api_latest.io.ComfyNode = object
sys.modules['comfy_api'] = MagicMock()
sys.modules['comfy_api.latest'] = _comfy_api_latest
