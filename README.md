# ComfyUI Constrain Resolution Node

A ComfyUI node that analyzes images and suggests optimal dimensions while preserving aspect ratio. This node is particularly useful in image-to-image and image-to-video workflows where maintaining aspect ratios and resolution constraints is crucial.

![image](https://github.com/user-attachments/assets/3c6784be-2b87-47c8-81f4-bd3050cc0719)

## Features

- Analyzes input images and suggests optimal dimensions
- Preserves aspect ratio while fitting within minimum and maximum resolution constraints
- Handles both landscape and portrait orientations
- Passes through the original image unmodified for chaining with other nodes
- Provides both constrained dimensions and aspect ratio information

## Inputs

- **Image**: The input image to analyze (required)
- **Min Resolution**: Minimum resolution in pixels for both width and height
- **Max Resolution**: Maximum resolution in pixels for both width and height

## Outputs

- **Image**: The unchanged input image (passed through)
- **Constrained Width**: Suggested width that fits within min/max constraints
- **Constrained Height**: Suggested height that fits within min/max constraints
- **Constrained Aspect Ratio**: The aspect ratio of the constrained dimensions
- **Original Aspect Ratio**: The original aspect ratio of the input image

## Usage

### Basic Workflow
1. Connect your image source to the `Image` input
2. Set your desired minimum and maximum resolution constraints
3. Connect the `Image` output to your preferred resize node (e.g., Image Resize)
4. Use the `Constrained Width` and `Constrained Height` outputs to set the dimensions in your resize node

Example:
![image](https://github.com/user-attachments/assets/70145782-490d-4a51-a458-71e0ec6e4c44)


### Common Use Cases

- **Image-to-Image**: Ensure consistent image sizes while maintaining aspect ratios
- **Image-to-Video**: Prepare frames with proper dimensions for video generation
- **Batch Processing**: Standardize image dimensions across multiple images
- **Resolution Optimization**: Find optimal dimensions for specific model requirements

## Installation

Use Comfy Manager or: 

1. Create a `custom_nodes` folder in your ComfyUI directory if it doesn't exist
2. Clone this repository into the `custom_nodes` folder:
    git clone https://github.com/EnragedAntelope/ComfyUI-Constrain-Resolution

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
