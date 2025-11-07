import numpy as np
from typing import Tuple
from comfy_api.latest import ComfyExtension, io


class ConstraintModeEnum(io.ComboInput):
    """Combo input for constraint mode selection"""
    OPTIONS = ["Prioritize Min Resolution", "Prioritize Max Resolution (Strict)"]


class ConstrainResolution(io.ComfyNode):
    """
    A ComfyUI node that analyzes images and suggests optimal dimensions
    while preserving aspect ratio.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        """Define the node schema with inputs and outputs"""
        return io.Schema(
            node_id="ConstrainResolution",
            display_name="Constrain Resolution",
            category="image/resolution",
            description="Analyzes images and suggests optimal dimensions while preserving aspect ratio",
            inputs=[
                io.Image.Input(
                    "image",
                    tooltip="Input image to analyze for resolution constraints"
                ),
                ConstraintModeEnum.Input(
                    "constraint_mode",
                    default="Prioritize Min Resolution",
                    tooltip="Choose how to handle conflicting constraints for extreme aspect ratios"
                ),
                io.Int.Input(
                    "min_res",
                    default=704,
                    min=1,
                    tooltip="Minimum resolution in pixels for both width and height"
                ),
                io.Int.Input(
                    "max_res",
                    default=1280,
                    min=1,
                    tooltip="Maximum resolution in pixels for both width and height"
                ),
                io.Int.Input(
                    "multiple_of",
                    default=8,
                    min=1,
                    tooltip="Ensure dimensions are multiples of this number (e.g., 8 for SDXL)"
                ),
            ],
            outputs=[
                io.Image.Output("image_passthrough"),
                io.Int.Output("constrained_width"),
                io.Int.Output("constrained_height"),
                io.Float.Output("constrained_aspect_ratio"),
                io.Float.Output("original_aspect_ratio"),
            ],
            is_output_node=False,
            is_deprecated=False,
            is_experimental=False
        )

    @staticmethod
    def calculate_aspect_ratio(width: int, height: int) -> float:
        """Calculate aspect ratio from width and height"""
        if height == 0:
            return 0.0
        return round(width / height, 4)

    @staticmethod
    def round_to_multiple(value: int, multiple: int) -> int:
        """Round a value to the nearest multiple of the specified number"""
        return multiple * round(value / multiple)

    @staticmethod
    def calculate_optimal_dimensions(
        width: int,
        height: int,
        min_res: int,
        max_res: int,
        multiple_of: int,
        constraint_mode: str
    ) -> Tuple[int, int]:
        """Calculate optimal dimensions based on constraints"""
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

    @classmethod
    def execute(cls, image, constraint_mode, min_res, max_res, multiple_of) -> io.NodeOutput:
        """Execute the node logic"""
        if max_res < min_res:
            raise ValueError(f"max_res ({max_res}) must be greater than or equal to min_res ({min_res})")

        height = image.shape[1]
        width = image.shape[2]

        original_aspect_ratio = cls.calculate_aspect_ratio(width, height)

        suggested_width, suggested_height = cls.calculate_optimal_dimensions(
            width, height, min_res, max_res, multiple_of, constraint_mode
        )

        final_aspect_ratio = cls.calculate_aspect_ratio(suggested_width, suggested_height)

        if original_aspect_ratio > 0:
            aspect_ratio_deviation = abs((final_aspect_ratio - original_aspect_ratio) / original_aspect_ratio * 100)
            if aspect_ratio_deviation > 1:  # 1% tolerance for rounding
                print(f"Warning: Aspect ratio deviation of {aspect_ratio_deviation:.2f}% detected due to rounding.")

        return io.NodeOutput(
            image,
            suggested_width,
            suggested_height,
            final_aspect_ratio,
            original_aspect_ratio
        )


class ConstrainResolutionExtension(ComfyExtension):
    """Extension class for registering nodes"""

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        """Return list of nodes provided by this extension"""
        return [ConstrainResolution]


async def comfy_entrypoint() -> ComfyExtension:
    """Entry point for ComfyUI v3"""
    return ConstrainResolutionExtension()
