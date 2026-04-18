import pytest
from nodes import ConstrainResolution, ConstraintMode

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
