import torch
import torch.nn.functional as F
from typing import Tuple
from comfy_api.latest import ComfyExtension, io
from enum import StrEnum


class ConstraintMode(StrEnum):
    """Constraint mode for handling extreme aspect ratios"""
    MIN_RES = "Prioritize Min Resolution"
    MAX_RES_STRICT = "Prioritize Max Resolution (Strict)"


class CropPosition(StrEnum):
    """Position for cropping when aspect ratios don't match"""
    CENTER = "center"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class ConstrainResolution(io.ComfyNode):
    """
    A ComfyUI node that analyzes and resizes images to optimal dimensions
    while preserving or constraining aspect ratio based on resolution limits.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        """Define the node schema with inputs and outputs"""
        return io.Schema(
            node_id="ConstrainResolution",
            display_name="Constrain Resolution",
            category="image/resolution",
            description=(
                "Intelligently resizes images to fit within resolution constraints while preserving aspect ratio. "
                "Perfect for preparing images for AI models with specific dimension requirements. "
                "\n\n"
                "💡 USAGE TIPS:\n"
                "• Use 'Prioritize Min Resolution' to ensure images are never too small (may exceed max on one dimension)\n"
                "• Use 'Prioritize Max Resolution (Strict)' for hard VRAM limits (may go below min on one dimension)\n"
                "• Set 'Multiple Of' to 8 for SDXL, 16 for some models, or 64 for optimal performance\n"
                "• 'Crop as Required' is enabled by default for immediate compatibility with strict dimension requirements\n"
                "• The node outputs both the resized image and the original for workflow flexibility"
            ),
            inputs=[
                # Image input
                io.Image.Input(
                    "image",
                    tooltip="Input image to analyze and resize"
                ),

                # Resolution constraints
                io.Int.Input(
                    "min_res",
                    default=704,
                    min=1,
                    max=65536,
                    tooltip="Minimum resolution in pixels for width and height. Images smaller than this will be upscaled."
                ),
                io.Int.Input(
                    "max_res",
                    default=1280,
                    min=1,
                    max=65536,
                    tooltip="Maximum resolution in pixels for width and height. Images larger than this will be downscaled."
                ),
                io.Int.Input(
                    "multiple_of",
                    default=8,
                    min=1,
                    max=256,
                    tooltip=(
                        "Ensures output dimensions are multiples of this number. "
                        "Common values: 8 (SDXL), 16 (some models), 32 or 64 (optimal performance). "
                        "Set to 1 to disable rounding."
                    )
                ),

                # Constraint behavior
                io.Input(
                    "constraint_mode",
                    ConstraintMode,
                    ConstraintMode.MIN_RES,  # Default value as a positional argument
                    tooltip=(
                        "How to handle conflicts when extreme aspect ratios make it impossible to satisfy both min and max.\n"
                        "• Prioritize Min Resolution: Ensures neither dimension falls below min_res (may exceed max_res)\n"
                        "• Prioritize Max Resolution (Strict): Strictly enforces max_res limit (may go below min_res)"
                    )
                ),

                # Crop options
                io.Boolean.Input(
                    "crop_as_required",
                    default=True,
                    tooltip=(
                        "Enable cropping to achieve exact target dimensions when rounding causes aspect ratio changes. "
                        "Disable if preserving the entire image is more important than exact dimensions."
                    )
                ),
                io.Input(
                    "crop_position",
                    CropPosition,
                    CropPosition.CENTER,  # Default value as a positional argument
                    tooltip=(
                        "Where to crop from when 'Crop as Required' is enabled.\n"
                        "• center: Crop equally from all sides\n"
                        "• top: Keep top portion, crop from bottom\n"
                        "• bottom: Keep bottom portion, crop from top\n"
                        "• left: Keep left portion, crop from right\n"
                        "• right: Keep right portion, crop from left"
                    )
                ),
            ],
            outputs=[
                io.Image.Output(
                    "resized_image",
                    tooltip="Image resized to the constrained dimensions"
                ),
                io.Image.Output(
                    "original_image",
                    tooltip="Original image passed through unchanged for workflow flexibility"
                ),
                io.Int.Output(
                    "width",
                    tooltip="Final width after constraints and rounding"
                ),
                io.Int.Output(
                    "height",
                    tooltip="Final height after constraints and rounding"
                ),
                io.Float.Output(
                    "final_aspect_ratio",
                    tooltip="Aspect ratio of the output image (width/height)"
                ),
                io.Float.Output(
                    "original_aspect_ratio",
                    tooltip="Aspect ratio of the input image for comparison"
                ),
            ],
            is_output_node=False,
            is_deprecated=False,
            is_experimental=False
        )

    @classmethod
    def validate_inputs(cls, min_res, max_res, multiple_of, **kwargs):
        """Validate input parameters"""
        if max_res < min_res:
            return f"max_res ({max_res}) must be greater than or equal to min_res ({min_res})"

        if multiple_of < 1:
            return f"multiple_of must be at least 1, got {multiple_of}"

        if min_res < 1:
            return f"min_res must be at least 1, got {min_res}"

        return True

    @staticmethod
    def calculate_aspect_ratio(width: int, height: int) -> float:
        """Calculate aspect ratio from width and height"""
        if height == 0:
            return 0.0
        return round(width / height, 4)

    @staticmethod
    def round_to_multiple(value: int, multiple: int) -> int:
        """Round a value to the nearest multiple of the specified number"""
        if multiple == 1:
            return value
        return max(multiple, multiple * round(value / multiple))

    @staticmethod
    def calculate_optimal_dimensions(
        width: int,
        height: int,
        min_res: int,
        max_res: int,
        multiple_of: int,
        constraint_mode: ConstraintMode
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
        if constraint_mode == ConstraintMode.MIN_RES:
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

    @staticmethod
    def resize_image(image: torch.Tensor, target_width: int, target_height: int) -> torch.Tensor:
        """
        Resize image tensor to target dimensions using bilinear interpolation.

        Args:
            image: Input tensor in format [batch, height, width, channels]
            target_width: Target width in pixels
            target_height: Target height in pixels

        Returns:
            Resized tensor in same format as input
        """
        # ComfyUI images are [batch, height, width, channels]
        # torch needs [batch, channels, height, width] for interpolate
        batch, height, width, channels = image.shape

        # Permute to [batch, channels, height, width]
        image_permuted = image.permute(0, 3, 1, 2)

        # Resize using bilinear interpolation
        resized = F.interpolate(
            image_permuted,
            size=(target_height, target_width),
            mode='bilinear',
            align_corners=False
        )

        # Permute back to [batch, height, width, channels]
        resized = resized.permute(0, 2, 3, 1)

        return resized

    @staticmethod
    def crop_image(
        image: torch.Tensor,
        target_width: int,
        target_height: int,
        position: CropPosition
    ) -> torch.Tensor:
        """
        Crop image to exact target dimensions from specified position.

        Args:
            image: Input tensor in format [batch, height, width, channels]
            target_width: Target width in pixels
            target_height: Target height in pixels
            position: One of "center", "top", "bottom", "left", "right"

        Returns:
            Cropped tensor
        """
        batch, height, width, channels = image.shape

        # Calculate crop amounts
        width_diff = width - target_width
        height_diff = height - target_height

        # No crop needed if dimensions match
        if width_diff == 0 and height_diff == 0:
            return image

        # Calculate crop coordinates based on position
        if position == CropPosition.CENTER:
            left = width_diff // 2
            top = height_diff // 2
        elif position == CropPosition.TOP:
            left = width_diff // 2
            top = 0
        elif position == CropPosition.BOTTOM:
            left = width_diff // 2
            top = height_diff
        elif position == CropPosition.LEFT:
            left = 0
            top = height_diff // 2
        elif position == CropPosition.RIGHT:
            left = width_diff
            top = height_diff // 2
        else:
            # Default to center
            left = width_diff // 2
            top = height_diff // 2

        # Ensure we don't go out of bounds
        left = max(0, min(left, width_diff))
        top = max(0, min(top, height_diff))

        # Crop the image
        right = left + target_width
        bottom = top + target_height

        cropped = image[:, top:bottom, left:right, :]

        return cropped

    @classmethod
    def execute(
        cls,
        image,
        min_res,
        max_res,
        multiple_of,
        constraint_mode,
        crop_as_required,
        crop_position
    ) -> io.NodeOutput:
        """Execute the node logic"""
        # Get original dimensions
        batch, height, width, channels = image.shape

        original_aspect_ratio = cls.calculate_aspect_ratio(width, height)

        # Calculate optimal dimensions
        target_width, target_height = cls.calculate_optimal_dimensions(
            width, height, min_res, max_res, multiple_of, constraint_mode
        )

        # Resize image to target dimensions
        resized_image = cls.resize_image(image, target_width, target_height)

        # Calculate aspect ratio after resize
        final_aspect_ratio = cls.calculate_aspect_ratio(target_width, target_height)

        # Check if cropping is needed and enabled
        if crop_as_required and original_aspect_ratio > 0:
            # Determine if we need to crop
            # After rounding to multiples, the aspect ratio might have changed slightly
            # We'll resize to maintain aspect ratio on the larger dimension, then crop

            aspect_ratio_deviation = abs((final_aspect_ratio - original_aspect_ratio) / original_aspect_ratio * 100)

            if aspect_ratio_deviation > 0.1:  # If more than 0.1% deviation
                # Resize to the dimension that needs to be larger, then crop
                if width / height > target_width / target_height:
                    # Original is wider, resize based on width and crop height
                    intermediate_height = int(target_width / (width / height))
                    resized_image = cls.resize_image(image, target_width, intermediate_height)
                else:
                    # Original is taller, resize based on height and crop width
                    intermediate_width = int(target_height * (width / height))
                    resized_image = cls.resize_image(image, intermediate_width, target_height)

                # Crop to exact target dimensions
                resized_image = cls.crop_image(resized_image, target_width, target_height, crop_position)

                print(f"Image cropped from center to achieve exact dimensions {target_width}x{target_height}")

        # Log aspect ratio deviation warning if significant
        if original_aspect_ratio > 0 and not crop_as_required:
            aspect_ratio_deviation = abs((final_aspect_ratio - original_aspect_ratio) / original_aspect_ratio * 100)
            if aspect_ratio_deviation > 1:  # 1% tolerance for rounding
                print(
                    f"ℹ️  Aspect ratio changed by {aspect_ratio_deviation:.2f}% due to rounding. "
                    f"Enable 'Crop as Required' to preserve exact aspect ratio."
                )

        return io.NodeOutput(
            resized_image,      # resized image
            image,              # original image passthrough
            target_width,       # final width
            target_height,      # final height
            final_aspect_ratio, # final aspect ratio
            original_aspect_ratio  # original aspect ratio
        )


class ConstrainResolutionExtension(ComfyExtension):
    """Extension class for registering nodes"""

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        """Return list of nodes provided by this extension"""
        return [ConstrainResolution]


async def comfy_entrypoint() -> ComfyExtension:
    """Entry point for ComfyUI v3"""
    return ConstrainResolutionExtension()
