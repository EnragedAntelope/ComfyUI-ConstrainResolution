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
                "multiple_of": ("INT", {
                    "default": 2,
                    "min": 1,
                    "tooltip": "Ensure dimensions are multiples of this number (e.g., 8 for SDXL, 16 for some models)"
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
    def round_to_multiple(value: int, multiple: int) -> int:
        """Round a value up to the nearest multiple of the specified number"""
        return ((value + multiple - 1) // multiple) * multiple

    @staticmethod
    def calculate_optimal_dimensions(width: int, height: int, min_res: int, max_res: int, multiple_of: int) -> Tuple[int, int]:
        aspect_ratio = width / height
        
        # Calculate maximum allowed pixels based on max_res x min_res
        max_pixels = max_res * min_res
        
        # Adjust min_res and max_res to be multiples of multiple_of
        min_res = ConstrainResolution.round_to_multiple(min_res, multiple_of)
        max_res = (max_res // multiple_of) * multiple_of  # Round down max_res
        
        if abs(aspect_ratio - 1.0) < 0.01:  # Square image (with small tolerance)
            # Calculate optimal square dimension based on max pixels
            optimal_dim = int(np.sqrt(max_pixels))
            # Round up to nearest multiple
            optimal_dim = ConstrainResolution.round_to_multiple(optimal_dim, multiple_of)
            # Ensure it's within min/max bounds
            optimal_dim = min(max(optimal_dim, min_res), max_res)
            return optimal_dim, optimal_dim
            
        if aspect_ratio > 1:  # Landscape
            # First try to set width to max_res
            width = max_res
            height = int(width / aspect_ratio)
            height = ConstrainResolution.round_to_multiple(height, multiple_of)
            
            # If total pixels exceed max_pixels, scale down proportionally
            if width * height > max_pixels:
                width = int(np.sqrt(max_pixels * aspect_ratio))
                width = ConstrainResolution.round_to_multiple(width, multiple_of)
                height = int(width / aspect_ratio)
                height = ConstrainResolution.round_to_multiple(height, multiple_of)
            
            # Check minimum bounds
            if height < min_res:
                height = min_res
                width = int(height * aspect_ratio)
                width = ConstrainResolution.round_to_multiple(width, multiple_of)
        else:  # Portrait
            # First try to set height to max_res
            height = max_res
            width = int(height * aspect_ratio)
            width = ConstrainResolution.round_to_multiple(width, multiple_of)
            
            # If total pixels exceed max_pixels, scale down proportionally
            if width * height > max_pixels:
                height = int(np.sqrt(max_pixels / aspect_ratio))
                height = ConstrainResolution.round_to_multiple(height, multiple_of)
                width = int(height * aspect_ratio)
                width = ConstrainResolution.round_to_multiple(width, multiple_of)
            
            # Check minimum bounds
            if width < min_res:
                width = min_res
                height = int(width / aspect_ratio)
                height = ConstrainResolution.round_to_multiple(height, multiple_of)

        # Final bounds check
        width = min(max(width, min_res), max_res)
        width = ConstrainResolution.round_to_multiple(width, multiple_of)
        height = min(max(height, min_res), max_res)
        height = ConstrainResolution.round_to_multiple(height, multiple_of)
        
        # Final pixel count check (just in case rounding pushed us over)
        while width * height > max_pixels:
            if width > height:
                width = width - multiple_of  # Reduce by multiple_of
            else:
                height = height - multiple_of
        
        # Final multiple check (just to be absolutely certain)
        width = ConstrainResolution.round_to_multiple(width, multiple_of)
        height = ConstrainResolution.round_to_multiple(height, multiple_of)
        
        return width, height

    def process(self, image, min_res, max_res, multiple_of):
        # Input validation
        if max_res <= min_res:
            raise ValueError(f"max_res ({max_res}) must be greater than min_res ({min_res})")
        
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
        suggested_width, suggested_height = self.calculate_optimal_dimensions(width, height, min_res, max_res, multiple_of)
        
        # Calculate final aspect ratio
        final_aspect_ratio = self.calculate_aspect_ratio(suggested_width, suggested_height)
        
        # Calculate aspect ratio deviation (as a percentage)
        aspect_ratio_deviation = abs((final_aspect_ratio - original_aspect_ratio) / original_aspect_ratio * 100)
        
        # Optional: Add warnings for significant changes
        if aspect_ratio_deviation > 10:  # More than 10% deviation
            print(f"Warning: Significant aspect ratio change: {aspect_ratio_deviation:.1f}% deviation from original")

        return (image, suggested_width, suggested_height, final_aspect_ratio, original_aspect_ratio)

NODE_CLASS_MAPPINGS = {
    "ConstrainResolution": ConstrainResolution
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConstrainResolution": "Constrain Resolution"
} 
