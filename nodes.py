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
        
        # Calculate maximum allowed pixels based on max_res x min_res
        max_pixels = max_res * min_res
        
        if abs(aspect_ratio - 1.0) < 0.01:  # Square image (with small tolerance)
            # Calculate optimal square dimension based on max pixels
            optimal_dim = int(np.sqrt(max_pixels))
            # Round up to nearest even number
            optimal_dim = optimal_dim + (optimal_dim % 2)
            # Ensure it's within min/max bounds
            optimal_dim = min(max(optimal_dim, min_res), max_res)
            return optimal_dim, optimal_dim
            
        if aspect_ratio > 1:  # Landscape
            # First try to set width to max_res
            width = max_res
            height = int(width / aspect_ratio)
            
            # If total pixels exceed max_pixels, scale down proportionally
            if width * height > max_pixels:
                width = int(np.sqrt(max_pixels * aspect_ratio))
                # Round up to nearest even number
                width = width + (width % 2)
                height = int(width / aspect_ratio)
                # Round up to nearest even number
                height = height + (height % 2)
            
            # Check minimum bounds
            if height < min_res:
                height = min_res
                width = int(height * aspect_ratio)
                width = width + (width % 2)
        else:  # Portrait
            # First try to set height to max_res
            height = max_res
            width = int(height * aspect_ratio)
            
            # If total pixels exceed max_pixels, scale down proportionally
            if width * height > max_pixels:
                height = int(np.sqrt(max_pixels / aspect_ratio))
                # Round up to nearest even number
                height = height + (height % 2)
                width = int(height * aspect_ratio)
                # Round up to nearest even number
                width = width + (width % 2)
            
            # Check minimum bounds
            if width < min_res:
                width = min_res
                height = int(width / aspect_ratio)
                height = height + (height % 2)

        # Final bounds check
        width = min(max(width, min_res), max_res)
        height = min(max(height, min_res), max_res)
        
        # Final pixel count check (just in case rounding pushed us over)
        while width * height > max_pixels:
            if width > height:
                width = width - 2  # Reduce by 2 to keep even numbers
            else:
                height = height - 2
        
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
