# ComfyUI Constrain Resolution Node

A [ComfyUI](https://github.com/comfyanonymous/ComfyUI) node that intelligently resizes images to optimal dimensions while preserving aspect ratio. This node is essential for image-to-image and image-to-video workflows where strict resolution constraints and dimension requirements must be met.

<img width="1496" height="911" alt="image" src="https://github.com/user-attachments/assets/601d71de-bafb-4dc1-ab9b-7022f13b7577" />

## Features

- **Intelligent Image Resizing**: Automatically resizes images using high-quality bilinear interpolation
- **Aspect Ratio Preservation**: Maintains original aspect ratio through smart cropping when needed
- **Flexible Constraint Modes**: Choose between prioritizing minimum resolution or strictly enforcing maximum limits
- **Multiple Alignment**: Ensures dimensions are multiples of specified values (e.g., 2, 8, 16, 32, 64 for performance)
- **Smart Cropping**: Optional cropping with configurable position (center, top, bottom, left, right)
- **Dual Outputs**: Provides both resized and original images for workflow flexibility
- **Comprehensive Validation**: Input validation prevents invalid configurations
- **Detailed Metrics**: Outputs width, height, and aspect ratio information for analysis

## Why Use This Node?

Many AI models have strict dimension requirements:
- **Image-to-Video models** often require exact resolutions (e.g., 1024x576, 768x768)
- **Modern diffusion models** (Flux, Stable Diffusion, etc.) typically work best with dimensions divisible by 2, 8, or higher
- **Some models** require dimensions divisible by 16, 32, or 64 for optimal performance
- **VRAM constraints** may require strict maximum resolution limits

This node handles all these requirements intelligently, ensuring your images are always compatible with downstream processes.

## Inputs

### Image Input
- **image**: The input image to analyze and resize (required)

### Resolution Constraints
- **min_res** (default: 704, range: 1-65536): Minimum resolution in pixels for both width and height. Images with any dimension smaller than this will be upscaled to meet the requirement.
- **max_res** (default: 1280, range: 1-65536): Maximum resolution in pixels for both width and height. Images with any dimension larger than this will be downscaled.
- **multiple_of** (default: 2, range: 1-256): Ensures output dimensions are multiples of this number. Common values:
  - `2` - Standard for most diffusion models (Flux, Stable Diffusion, etc.)
  - `8` or `16` - Some models with stricter alignment requirements
  - `32` or `64` - Optimal for certain architectures and performance
  - `1` - Disable rounding (use exact calculated dimensions)

### Constraint Behavior
- **constraint_mode** (default: "Prioritize Min Resolution"): How to handle conflicts when extreme aspect ratios make it impossible to satisfy both min and max constraints.
  - **Prioritize Min Resolution**: Ensures neither dimension falls below `min_res`. For extreme aspect ratios, this may cause the longer dimension to exceed `max_res`. Recommended for most workflows to prevent images that are too small.
  - **Prioritize Max Resolution (Strict)**: Strictly enforces the `max_res` limit on both dimensions, guaranteeing output fits within a `max_res × max_res` bounding box. For extreme aspect ratios, the shorter dimension may fall below `min_res`. Useful for strict VRAM limits.

### Crop Options
- **crop_as_required** (default: **True**): Enable cropping to achieve exact target dimensions when rounding to multiples causes aspect ratio changes.
  - **Enabled** (recommended): Preserves aspect ratio perfectly by cropping minimal amounts. Output is immediately compatible with strict dimension requirements.
  - **Disabled**: Preserves entire image but may slightly distort aspect ratio due to rounding.

- **crop_position** (default: "center"): Where to crop from when `crop_as_required` is enabled. Only applies when cropping is active.
  - **center**: Crop equally from all sides (default, works for most cases)
  - **top**: Keep top portion, crop from bottom (useful for portraits, headshots)
  - **bottom**: Keep bottom portion, crop from top (useful for product shots on surfaces)
  - **left**: Keep left portion, crop from right (useful for documents, reading order)
  - **right**: Keep right portion, crop from left (useful for RTL content)

## Outputs

The node provides six outputs for maximum workflow flexibility:

1. **resized_image**: The final image resized and optionally cropped to meet all constraints. This is your primary output for use in downstream nodes.
2. **original_image**: The input image passed through unchanged. Useful for comparison or parallel workflows.
3. **width**: Final output width in pixels after all constraints and rounding.
4. **height**: Final output height in pixels after all constraints and rounding.
5. **final_aspect_ratio**: Aspect ratio of the output image (width/height), rounded to 4 decimal places.
6. **original_aspect_ratio**: Aspect ratio of the input image for comparison.

## Usage

### Basic Workflow

1. Add the **Constrain Resolution** node to your workflow
2. Connect your image source to the `image` input
3. Set your desired `min_res` and `max_res` constraints
4. Set `multiple_of` based on your model requirements (2 for most models, 8/16/32/64 for specific architectures)
5. Choose your `constraint_mode` (keep default for most cases)
6. Keep `crop_as_required` enabled for exact dimensions (recommended)
7. Connect the `resized_image` output to your next node (resize node, image-to-video, etc.)

Example workflow:
![image](https://github.com/user-attachments/assets/36dd312c-4a65-44ce-aead-fb7cbe65c72c)

### Common Use Cases

#### Image-to-Video Workflows
```
Load Image → Constrain Resolution → Image-to-Video Model
Settings: min_res=768, max_res=1024, multiple_of=8, crop_as_required=True
```
Ensures images meet exact dimension requirements for video generation models.

#### Diffusion Model Image-to-Image
```
Load Image → Constrain Resolution → Model Upscale/I2I
Settings: min_res=704, max_res=1280, multiple_of=2, constraint_mode="Prioritize Min Resolution"
```
Optimizes images for diffusion model processing while maintaining quality.

#### Batch Processing with VRAM Limits
```
Load Images (Batch) → Constrain Resolution → Model Processing
Settings: max_res=1024, constraint_mode="Prioritize Max Resolution (Strict)", crop_as_required=True
```
Ensures no image exceeds VRAM capacity while processing batches.

#### Portrait Cropping for Headshots
```
Load Image → Constrain Resolution → Output
Settings: min_res=512, max_res=768, crop_as_required=True, crop_position="top"
```
Intelligently crops portraits to keep faces (typically in upper portion).

### Advanced Tips

- **Extreme Aspect Ratios**: For very wide or very tall images (e.g., panoramas, screenshots), use "Prioritize Max Resolution (Strict)" to prevent excessive upscaling on one dimension.

- **Preserving Every Pixel**: If you absolutely need to keep the entire image without cropping, set `crop_as_required=False` and `multiple_of=1`. Note that this may produce dimensions that aren't optimal for all models.

- **Quality vs. Speed**: Higher `multiple_of` values (32, 64) can improve processing speed in some models but may crop more aggressively. Test to find the sweet spot for your workflow.

- **Aspect Ratio Monitoring**: Use the `final_aspect_ratio` and `original_aspect_ratio` outputs to monitor how much the aspect ratio changed. Connect these to display nodes to track during batch processing.

## Technical Details

### Resizing Algorithm
- Uses PyTorch's `F.interpolate` with bilinear interpolation and `align_corners=False`
- Maintains proper tensor shape handling: `[batch, height, width, channels]`
- High-quality resizing suitable for AI model inputs

### Cropping Algorithm
When `crop_as_required` is enabled:
1. Image is first resized to preserve aspect ratio on the larger dimension
2. Minimal cropping is applied to achieve exact target dimensions
3. Crop position determines which portion of the image is preserved
4. This approach maximizes quality by minimizing information loss

### Input Validation
The node validates:
- `max_res` must be ≥ `min_res`
- `min_res` must be ≥ 1
- `multiple_of` must be ≥ 1
- All values must be within reasonable bounds (up to 65536 for resolutions)

## Installation

### Using ComfyUI Manager (Recommended)
1. Open ComfyUI Manager
2. Search for "Constrain Resolution"
3. Click Install
4. Restart ComfyUI

### Manual Installation
1. Navigate to your `ComfyUI/custom_nodes/` directory
2. Clone this repository:
   ```bash
   git clone https://github.com/EnragedAntelope/ComfyUI-ConstrainResolution.git
   ```
3. Restart ComfyUI

The node will automatically install its dependencies (`numpy`).

## ComfyUI v3 Compatibility

This node is built using the **ComfyUI v3 specification** with the following modern features:
- Uses `comfy_api.latest` for future-proof compatibility
- Object-oriented schema with `io.ComfyNode` base class
- Type-safe inputs and outputs with comprehensive tooltips
- Stateless execution model with classmethod-based `execute()`
- Input validation with `validate_inputs()`
- Fully async-compatible entry point

## Version History

- **v2.1.0**: Added image resizing, intelligent cropping, crop position control, comprehensive tooltips, input validation, and 65k resolution support
- **v2.0.0**: Migrated to ComfyUI v3 specification
- **v1.1**: Initial release with resolution analysis and constraint calculation

## License

See the [LICENSE](LICENSE) file for details.

## Contributing

Issues and pull requests are welcome! Please ensure any changes maintain compatibility with ComfyUI v3 specification.

## Support

If you encounter issues or have questions:
- Open an issue on [GitHub](https://github.com/EnragedAntelope/ComfyUI-ConstrainResolution/issues)
- Check existing issues for solutions
- Provide example images and settings when reporting problems
