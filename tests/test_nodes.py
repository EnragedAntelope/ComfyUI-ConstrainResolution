import sys

import pytest
import torch
from nodes import ConstrainResolution, ConstraintMode, ResizeMethod

STRICT = ConstraintMode.MAX_RES_STRICT.value
MIN = ConstraintMode.MIN_RES.value

calc = ConstrainResolution.calculate_optimal_dimensions


class TestMaxResStrict:
    def test_regression_500x333_2160_32(self):
        """Reported bug: 500x333 with max_res=2160, multiple_of=32 was producing 2176x1440."""
        w, h = calc(500, 333, 704, 2160, 32, STRICT)
        assert w <= 2160, f"width {w} exceeds max_res 2160"
        assert h <= 2160, f"height {h} exceeds max_res 2160"
        assert w % 32 == 0, f"width {w} not divisible by 32"
        assert h % 32 == 0, f"height {h} not divisible by 32"
        assert w == 2144
        assert h == 1440

    def test_max_res_exact_multiple_of_divisor(self):
        """When max_res is already a valid multiple, no over-clamp should occur."""
        w, h = calc(500, 333, 704, 2048, 32, STRICT)
        assert w <= 2048
        assert h <= 2048
        assert w % 32 == 0
        assert h % 32 == 0

    def test_portrait_image(self):
        """Portrait 333x500 should also respect the strict max_res limit."""
        w, h = calc(333, 500, 704, 2160, 32, STRICT)
        assert w <= 2160, f"width {w} exceeds max_res 2160"
        assert h <= 2160, f"height {h} exceeds max_res 2160"
        assert w % 32 == 0
        assert h % 32 == 0

    def test_square_image(self):
        """Square image: both dimensions should stay at or below max_res."""
        w, h = calc(1000, 1000, 704, 2160, 32, STRICT)
        assert w <= 2160
        assert h <= 2160
        assert w % 32 == 0
        assert h % 32 == 0
        assert w == h

    def test_multiple_of_1_no_rounding(self):
        """With multiple_of=1, output should be exactly max_res on the long side."""
        w, h = calc(500, 333, 704, 2160, 1, STRICT)
        assert w <= 2160
        assert h <= 2160
        assert w == 2160

    def test_multiple_of_64(self):
        """Larger divisor — strict max should still hold."""
        w, h = calc(500, 333, 704, 2160, 64, STRICT)
        assert w <= 2160
        assert h <= 2160
        assert w % 64 == 0
        assert h % 64 == 0

    def test_already_small_image_scales_up(self):
        """Small image should scale up to near max_res."""
        w, h = calc(100, 100, 64, 1024, 64, STRICT)
        assert w <= 1024
        assert h <= 1024
        assert w % 64 == 0
        assert h % 64 == 0

    def test_zero_dimensions(self):
        """Zero-dimension input should return (0, 0) without error."""
        w, h = calc(0, 0, 704, 2160, 32, STRICT)
        assert w == 0
        assert h == 0


class TestMinRes:
    def test_min_res_mode_unaffected_by_strict_clamp(self):
        """MIN_RES mode is allowed to exceed max_res when needed to meet min_res."""
        # Use extreme aspect ratio to force one dim below min_res
        w, h = calc(1000, 100, 704, 1000, 1, MIN)
        # The short dimension should be at least min_res
        assert min(w, h) >= 704

    def test_min_res_normal_case(self):
        """In MIN_RES mode with no extreme ratio, both dims should stay within normal range."""
        w, h = calc(500, 333, 704, 2048, 32, MIN)
        assert w % 32 == 0
        assert h % 32 == 0
        assert min(w, h) >= 704


class TestRoundToMultiple:
    def test_exact_multiple(self):
        assert ConstrainResolution.round_to_multiple(2048, 32) == 2048

    def test_rounds_to_nearest(self):
        # 2144 / 32 = 67.0 → stays 2144
        assert ConstrainResolution.round_to_multiple(2144, 32) == 2144

    def test_half_rounds_to_even(self):
        # 2160 / 32 = 67.5 → banker's rounding → 68 → 2176
        assert ConstrainResolution.round_to_multiple(2160, 32) == 2176

    def test_multiple_of_1_is_identity(self):
        assert ConstrainResolution.round_to_multiple(1999, 1) == 1999

    def test_minimum_floor(self):
        assert ConstrainResolution.round_to_multiple(1, 32) == 32


def run_node(image, **overrides):
    """Call execute() and return the positional outputs captured by the mocked io.NodeOutput."""
    mock_io = sys.modules['comfy_api.latest'].io
    params = dict(
        min_res=704,
        max_res=1280,
        multiple_of=2,
        resize_method=ResizeMethod.BILINEAR.value,
        constraint_mode=MIN,
        crop_as_required=True,
        crop_position="center",
    )
    params.update(overrides)
    mock_io.NodeOutput.reset_mock()
    ConstrainResolution.execute(image=image, **params)
    return mock_io.NodeOutput.call_args.args


class TestExecuteShapes:
    @pytest.mark.parametrize("size", [
        (500, 333), (333, 500), (1000, 1000), (1920, 1080),
        (101, 997), (2543, 1071), (1001, 1000), (703, 704),
    ])
    def test_output_shape_matches_reported_dims(self, size):
        """The resized tensor must exactly match the reported width/height outputs."""
        w, h = size
        image = torch.rand(1, h, w, 3)
        resized, original, out_w, out_h, _, _ = run_node(image, multiple_of=32)
        assert resized.shape == (1, out_h, out_w, 3)
        assert original.shape == image.shape

    def test_no_crop_shape_still_matches(self):
        image = torch.rand(1, 333, 500, 3)
        resized, _, out_w, out_h, _, _ = run_node(image, crop_as_required=False, multiple_of=32)
        assert resized.shape == (1, out_h, out_w, 3)


class TestResizeMethods:
    @pytest.mark.parametrize("method", [e.value for e in ResizeMethod])
    def test_all_methods_produce_target_shape(self, method):
        image = torch.rand(2, 100, 150, 3)
        out = ConstrainResolution.resize_image(image, 300, 200, method)
        assert out.shape == (2, 200, 300, 3)

    @pytest.mark.parametrize("method", ["bicubic", "lanczos"])
    def test_overshoot_is_clamped(self, method):
        image = torch.rand(1, 64, 64, 3)
        out = ConstrainResolution.resize_image(image, 128, 128, method)
        assert out.min() >= 0.0
        assert out.max() <= 1.0


class TestCropImage:
    @pytest.mark.parametrize("position", ["center", "top", "bottom", "left", "right"])
    def test_crop_positions_yield_exact_dims(self, position):
        image = torch.rand(1, 120, 200, 3)
        out = ConstrainResolution.crop_image(image, 100, 100, position)
        assert out.shape == (1, 100, 100, 3)
