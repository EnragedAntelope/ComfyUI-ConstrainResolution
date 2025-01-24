import numpy as np
from typing import Tuple

class ConstrainResolution:
    """
    A ComfyUI node that analyzes images and suggests optimal dimensions 
    while preserving aspect ratio.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """Define input types with tooltips"""
        return {
            "required": {
                "image": ("IMAGE", {
                    "tooltip": "Input image to analyze for resolution constraints"
                }),
                "min_res": ("INT", {
                    "default": 704,
                    "min": 1,
                    "tooltip": "Minimum resolution in pixels for both width and height"
                }),
                "max_res": ("INT", {
                    "default": 1280,
                    "min": 1,
                    "tooltip": "Maximum resolution in pixels for both width and height"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("image_passthrough", "constrained_width", "constrained_height", "constrained_aspect_ratio", "original_aspect_ratio")
    
    # Add tooltips for outputs
    RETURN_TYPES_TOOLTIPS = {
        "image_passthrough": "The unchanged input image (passed through)",
        "constrained_width": "Suggested width that fits within min/max constraints while preserving aspect ratio",
        "constrained_height": "Suggested height that fits within min/max constraints while preserving aspect ratio",
        "constrained_aspect_ratio": "The aspect ratio of the constrained dimensions",
        "original_aspect_ratio": "The original aspect ratio of the input image"
    }
    
    FUNCTION = "process"
    CATEGORY = "image/resolution"

    @staticmethod
    def calculate_aspect_ratio(width: int, height: int) -> float:
        return round(width / height, 4)

    @staticmethod
    def calculate_optimal_dimensions(width: int, height: int, min_res: int, max_res: int) -> Tuple[int, int]:
        aspect_ratio = width / height
        
        if aspect_ratio > 1:  # Landscape
            if width > max_res:
                width = max_res
                height = int(width / aspect_ratio)
            if height < min_res:
                height = min_res
                width = int(height * aspect_ratio)
        else:  # Portrait
            if height > max_res:
                height = max_res
                width = int(height * aspect_ratio)
            if width < min_res:
                width = min_res
                height = int(width / aspect_ratio)

        # Final bounds check
        width = min(max(width, min_res), max_res)
        height = min(max(height, min_res), max_res)
        
        return width, height

    def process(self, image, min_res, max_res):
        # Get image dimensions
        if len(image.shape) == 4:
            height = image.shape[1]
            width = image.shape[2]
        else:
            height = image.shape[0]
            width = image.shape[1]

        # Calculate original aspect ratio
        original_aspect_ratio = self.calculate_aspect_ratio(width, height)

        # Calculate optimal dimensions
        suggested_width, suggested_height = self.calculate_optimal_dimensions(width, height, min_res, max_res)
        
        # Calculate final aspect ratio
        aspect_ratio = self.calculate_aspect_ratio(suggested_width, suggested_height)

        # Return image first, followed by other outputs
        return (image, suggested_width, suggested_height, aspect_ratio, original_aspect_ratio)

NODE_CLASS_MAPPINGS = {
    "ConstrainResolution": ConstrainResolution
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConstrainResolution": "Constrain Resolution"
} 
