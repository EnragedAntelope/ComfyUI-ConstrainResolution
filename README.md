# ComfyUI Constrain Resolution Node

A [ComfyUI](https://github.com/comfyanonymous/ComfyUI) node that analyzes images and suggests optimal dimensions while preserving aspect ratio. This node is particularly useful in image-to-image and image-to-video workflows where maintaining aspect ratios and resolution constraints is crucial.

<img width="1496" height="911" alt="image" src="https://github.com/user-attachments/assets/601d71de-bafb-4dc1-ab9b-7022f13b7577" />


## Features

-   Analyzes input images and suggests optimal dimensions.
-   Preserves aspect ratio while fitting within minimum and maximum resolution constraints.
-   Ensures dimensions are multiples of a specified number (e.g., 8 for SDXL).
-   Handles both landscape and portrait orientations.
-   **Optional priority setting** to choose between strictly enforcing maximum resolution or ensuring minimum resolution is always met.
-   Passes through the original image unmodified for chaining with other nodes.
-   Provides both constrained dimensions and aspect ratio information.

## Inputs

-   **Image**: The input image to analyze (required).
-   **Constraint Mode**: Choose how to handle conflicting constraints for extreme aspect ratios.
    -   **Prioritize Min Resolution (Default)**: Ensures that neither dimension will be smaller than `min_res`. This is the recommended mode for most workflows, as it prevents generating images that are too small. In cases of extreme aspect ratios, this may cause the longer dimension to exceed `max_res`.
    -   **Prioritize Max Resolution (Strict)**: Strictly enforces the `max_res` limit on both dimensions. This guarantees the output will fit within a `max_res` x `max_res` bounding box, which is useful for strict VRAM limits. In cases of extreme aspect ratios, this may cause the shorter dimension to fall below `min_res`.
-   **Min Resolution**: Minimum resolution in pixels for either width or height.
-   **Max Resolution**: Maximum resolution in pixels for either width or height.
-   **Multiple Of**: Ensure dimensions are multiples of this number (e.g., 8 for SD-XL).

## Outputs

-   **Image**: The unchanged input image (passed through).
-   **Constrained Width**: Suggested width that fits the constraints.
-   **Constrained Height**: Suggested height that fits the constraints.
-   **Constrained Aspect Ratio**: The aspect ratio of the constrained dimensions.
-   **Original Aspect Ratio**: The original aspect ratio of the input image.

## Usage

### Basic Workflow

1.  Connect your image source to the `Image` input.
2.  Select your desired `Constraint Mode`. For most uses, the default is ideal.
3.  Set your desired `Min Resolution` and `Max Resolution` constraints.
4.  Set the `Multiple Of` value based on your model requirements (e.g., 8 for SDXL).
5.  Connect the `Image` output to your preferred resize node (e.g., Image Resize).
6.  Use the `Constrained Width` and `Constrained Height` outputs to set the dimensions in your resize node.

Example:
![image](https://github.com/user-attachments/assets/36dd312c-4a65-44ce-aead-fb7cbe65c72c)

### Common Use Cases

-   **Image-to-Image**: Ensure consistent image sizes while maintaining aspect ratios.
-   **Image-to-Video**: Prepare frames with proper dimensions for video generation.
-   **Batch Processing**: Standardize image dimensions across multiple images.
-   **Resolution Optimization**: Find optimal dimensions for specific model requirements.
-   **VRAM Management**: Use "Prioritize Max Resolution" mode to avoid exceeding VRAM limits with unusually large images.

## Installation

Use [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) or follow these manual installation steps:

1.  Navigate to your `ComfyUI/custom_nodes/` directory.
2.  Clone this repository:
    ```bash
    git clone https://github.com/EnragedAntelope/ComfyUI-ConstrainResolution.git
    ```
3.  Restart ComfyUI.

## License

See the [LICENSE](LICENSE) file for details.
