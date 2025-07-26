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
                "constraint_mode": (["Prioritize Min Resolution", "Prioritize Max Resolution (Strict)"], {
                    "default": "Prioritize Min Resolution",
                    "tooltip": "Choose how to handle conflicting constraints for extreme aspect ratios"
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
                    "default": 8,
                    "min": 1,
                    "tooltip": "Ensure dimensions are multiples of this number (e.g., 8 for SDXL)"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("image_passthrough", "constrained_width", "constrained_height", "constrained_aspect_ratio", "original_aspect_ratio")
    
    FUNCTION = "process"
    CATEGORY = "image/resolution"

    @staticmethod
    def calculate_aspect_ratio(width: int, height: int) -> float:
        if height == 0:
            return 0.0
        return round(width / height, 4)

    @staticmethod
    def round_to_multiple(value: int, multiple: int) -> int:
        """Round a value to the nearest multiple of the specified number"""
        return multiple * round(value / multiple)

    @staticmethod
    def calculate_optimal_dimensions(width: int, height: int, min_res: int, max_res: int, multiple_of: int, constraint_mode: str) -> Tuple[int, int]:
        if height == 0 or width == 0:
            return 0, 0
        
        aspect_ratio = width / height

        # 1. Initial scaling to fit the longest side to max_res
        if aspect_ratio >= 1:  # Landscape or square
            new_width = max_res
            new_height = new_width / aspect_ratio
        else:  # Portrait
            new_height = max_res
            new_width = new_height * aspect_ratio

        # 2. Apply constraint logic based on user's choice
        if constraint_mode == "Prioritize Min Resolution":
            # If a dimension is below min_res, scale the entire image up to meet it
            scale_factor = 1.0
            if new_width < min_res:
                scale_factor = max(scale_factor, min_res / new_width)
            if new_height < min_res:
                scale_factor = max(scale_factor, min_res / new_height)
            
            new_width *= scale_factor
            new_height *= scale_factor
        
        # If mode is "Prioritize Max Resolution (Strict)", we do nothing here.
        # The initial scaling already guarantees we are within the max_res bounds,
        # and we accept that a dimension may fall below min_res.

        # 3. Round final dimensions to the nearest multiple
        final_width = ConstrainResolution.round_to_multiple(int(new_width), multiple_of)
        final_height = ConstrainResolution.round_to_multiple(int(new_height), multiple_of)

        return final_width, final_height

    def process(self, image, constraint_mode, min_res, max_res, multiple_of):
        if max_res < min_res:
            raise ValueError(f"max_res ({max_res}) must be greater than or equal to min_res ({min_res})")
        
        height = image.shape[1]
        width = image.shape[2]

        original_aspect_ratio = self.calculate_aspect_ratio(width, height)

        suggested_width, suggested_height = self.calculate_optimal_dimensions(width, height, min_res, max_res, multiple_of, constraint_mode)
        
        final_aspect_ratio = self.calculate_aspect_ratio(suggested_width, suggested_height)
        
        if original_aspect_ratio > 0:
            aspect_ratio_deviation = abs((final_aspect_ratio - original_aspect_ratio) / original_aspect_ratio * 100)
            if aspect_ratio_deviation > 1: # 1% tolerance for rounding
                print(f"Warning: Aspect ratio deviation of {aspect_ratio_deviation:.2f}% detected due to rounding.")
        
        return (image, suggested_width, suggested_height, final_aspect_ratio, original_aspect_ratio)

NODE_CLASS_MAPPINGS = {
    "ConstrainResolution": ConstrainResolution
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConstrainResolution": "Constrain Resolution"
}
