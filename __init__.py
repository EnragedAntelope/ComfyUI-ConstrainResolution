import logging

logger = logging.getLogger(__name__)

try:
    from .nodes import comfy_entrypoint
    __all__ = ['comfy_entrypoint']
except (ImportError, SystemError):
    # Without this log the pack just silently fails to appear in ComfyUI,
    # leaving nothing to diagnose.
    logger.exception("ComfyUI-ConstrainResolution failed to load; its node will be unavailable.")
    __all__ = []
