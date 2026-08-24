import inspect
import sys
import types

import pytest
import torch

from nodes import (
    MAX_MULTIPLE_OF,
    MAX_OUTPUT_PIXELS,
    MAX_RESOLUTION,
    ConstrainResolution,
    ConstraintMode,
    ResizeMethod,
)

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

    def test_rounding_never_drops_below_min_res(self):
        """Nearest-multiple rounding must not violate the min_res guarantee.

        min_res=1100 with multiple_of=256: 1100 would round to 1024 (< min_res);
        it must be bumped up to 1280 instead.
        """
        w, h = calc(1000, 1000, 1100, 4096, 256, MIN)
        assert min(w, h) >= 1100
        assert w % 256 == 0
        assert h % 256 == 0

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


class TestExecuteGuards:
    def test_zero_dimension_input_passes_through(self):
        """A malformed tensor with a zero dimension must pass through, not crash the resizer."""
        image = torch.rand(1, 0, 500, 3)
        resized, original, out_w, out_h, _, _ = run_node(image)
        assert resized.shape == image.shape
        assert original.shape == image.shape
        assert (out_w, out_h) == (500, 0)

    def test_extreme_ratio_min_res_warns(self, caplog):
        """Extreme aspect ratio in MIN_RES mode should warn about the large upscale."""
        image = torch.rand(1, 100, 1000, 3)
        with caplog.at_level("WARNING"):
            run_node(image, constraint_mode=MIN)
        assert any("Upscaling by" in r.message for r in caplog.records)

    @pytest.mark.parametrize("mode", [MIN, STRICT])
    def test_normal_image_does_not_warn(self, caplog, mode):
        """A normal image must not trigger the upscale warning in either mode."""
        image = torch.rand(1, 800, 1000, 3)
        with caplog.at_level("WARNING"):
            run_node(image, constraint_mode=mode)
        assert not any("Upscaling by" in r.message for r in caplog.records)

    def test_strict_mode_large_upscale_warns(self, caplog):
        """Strict mode bounds the size, not the blur: a tiny source blown up
        12.8x deserves the same log signal min-res mode gives."""
        image = torch.rand(1, 100, 100, 3)
        with caplog.at_level("WARNING"):
            run_node(image, constraint_mode=STRICT)
        assert any("Upscaling by" in r.message for r in caplog.records)


class TestUpscaleBudget:
    """A tiny sliver of an image must not be blown up into a multi-GB tensor."""

    def test_extreme_ratio_raises_instead_of_exhausting_memory(self):
        # 1x690 at the stock defaults previously asked for 704x485760 (~4.1 GB
        # per batch item), which OOM-killed the ComfyUI process.
        with pytest.raises(ValueError, match="safety limit"):
            calc(1, 690, 704, 1280, 2, MIN)

    def test_error_names_the_escape_hatch(self):
        with pytest.raises(ValueError, match="Prioritize Max Resolution"):
            calc(8, 4000, 704, 1280, 2, MIN)

    def test_strict_mode_has_no_budget_error(self):
        """Strict mode is already bounded, so the same input must succeed."""
        w, h = calc(1, 690, 704, 1280, 2, STRICT)
        assert w <= 1280 and h <= 1280

    @pytest.mark.parametrize("size", [(1000, 100), (100, 1000), (3000, 1000), (1920, 1080)])
    def test_reasonable_ratios_still_allowed(self, size):
        """Ordinary and moderately wide images must not trip the budget."""
        w, h = calc(*size, 704, 1280, 2, MIN)
        assert min(w, h) >= 704

    def test_budget_scales_with_max_res(self):
        """A larger max_res raises the ceiling rather than being a fixed cap."""
        with pytest.raises(ValueError):
            calc(1, 100, 704, 1280, 2, MIN)
        w, h = calc(1, 100, 704, 2048, 2, MIN)
        assert min(w, h) >= 704

    def test_budget_has_an_absolute_ceiling(self):
        """The relative budget grows with max_res squared, so on its own it
        stops guarding anything at large max_res: 704x281600 is ~2.4 GB per
        batch item, which the multiplier alone would have waved through."""
        with pytest.raises(ValueError, match="safety limit"):
            calc(1, 400, 704, 8192, 2, MIN)

    def test_ceiling_never_refuses_the_users_own_max_res_box(self):
        """Strict mode allows a full max_res x max_res output, so min-res mode
        must not refuse the same size just because it exceeds the ceiling."""
        w, h = calc(1000, 1000, 16384, 16384, 2, MIN)
        assert w * h > MAX_OUTPUT_PIXELS
        assert w == h == 16384


class TestDegenerateConfigs:
    """Configurations that used to yield a zero dimension and a silent no-op."""

    def test_multiple_of_larger_than_max_res_raises(self):
        # Previously returned (0, 0), which execute() turned into a silent
        # passthrough logged as if the *input* had a zero dimension.
        with pytest.raises(ValueError, match="larger than max_res"):
            calc(512, 512, 8, 200, 256, STRICT)

    def test_thin_strip_does_not_collapse_to_zero_width(self):
        # int() truncation drove this to a width of 0 when multiple_of == 1.
        w, h = calc(1, 677, 8, 65, 1, STRICT)
        assert w >= 1 and h >= 1

    @pytest.mark.parametrize("mode", [MIN, STRICT])
    def test_multiple_of_zero_raises_not_zero_division(self, mode):
        with pytest.raises(ValueError, match="multiple_of"):
            calc(500, 333, 704, 1280, 0, mode)

    def test_round_to_multiple_rejects_zero(self):
        with pytest.raises(ValueError, match="multiple_of"):
            ConstrainResolution.round_to_multiple(100, 0)

    def test_round_to_multiple_never_returns_zero(self):
        assert ConstrainResolution.round_to_multiple(0, 1) == 1
        assert ConstrainResolution.round_to_multiple(0, 32) == 32

    def test_unknown_constraint_mode_raises(self):
        # Falling through applied neither the min floor nor the max clamp,
        # silently violating both limits.
        with pytest.raises(ValueError, match="Unknown constraint_mode"):
            calc(1000, 100, 704, 1280, 32, "TypoMode")


class TestCropGuards:
    def test_crop_larger_than_source_raises(self):
        image = torch.rand(1, 50, 50, 3)
        with pytest.raises(ValueError, match="cannot grow"):
            ConstrainResolution.crop_image(image, 100, 100, "center")

    def test_partial_overflow_also_raises(self):
        """Silently returned 50x30 instead of the requested 100x30."""
        image = torch.rand(1, 50, 50, 3)
        with pytest.raises(ValueError, match="cannot grow"):
            ConstrainResolution.crop_image(image, 100, 30, "center")

    def test_exact_size_is_a_no_op(self):
        image = torch.rand(1, 50, 60, 3)
        assert ConstrainResolution.crop_image(image, 60, 50, "center") is image


class TestSingleResize:
    def test_crop_path_resizes_only_once(self, monkeypatch):
        """The crop path used to compute a full resize and throw it away."""
        calls = []
        real = ConstrainResolution.resize_image

        def counting(image, w, h, method=None):
            calls.append((w, h))
            return real(image, w, h, method)

        monkeypatch.setattr(ConstrainResolution, "resize_image", staticmethod(counting))
        image = torch.rand(1, 1013, 1800, 3)
        resized, _, out_w, out_h, _, _ = run_node(image, multiple_of=32)
        assert len(calls) == 1, f"expected a single resize, got {calls}"
        assert resized.shape == (1, out_h, out_w, 3)

    def test_no_crop_path_resizes_only_once(self, monkeypatch):
        calls = []
        real = ConstrainResolution.resize_image

        def counting(image, w, h, method=None):
            calls.append((w, h))
            return real(image, w, h, method)

        monkeypatch.setattr(ConstrainResolution, "resize_image", staticmethod(counting))
        image = torch.rand(1, 1000, 1000, 3)
        run_node(image, crop_as_required=False, multiple_of=32)
        assert len(calls) == 1


class TestValidateInputs:
    def test_signature_has_no_kwargs(self):
        """**kwargs makes ComfyUI skip its own range and combo validation for
        every input on this node (execution.py: validate_has_kwargs)."""
        spec = inspect.getfullargspec(ConstrainResolution.validate_inputs.__func__)
        assert spec.varkw is None
        assert spec.varargs is None
        assert spec.args == ["cls", "min_res", "max_res", "multiple_of", "constraint_mode"]

    def test_accepts_valid_inputs(self):
        assert ConstrainResolution.validate_inputs(704, 1280, 2, MIN) is True

    def test_rejects_max_below_min(self):
        assert isinstance(ConstrainResolution.validate_inputs(1280, 704, 2, MIN), str)

    def test_rejects_bad_multiple_and_min(self):
        assert isinstance(ConstrainResolution.validate_inputs(704, 1280, 0, MIN), str)
        assert isinstance(ConstrainResolution.validate_inputs(0, 1280, 2, MIN), str)

    def test_strict_mode_rejects_multiple_of_above_max_res_at_queue_time(self):
        # calculate_optimal_dimensions raises this at execution time; catching
        # it in validate_inputs rejects the workflow when it is queued instead.
        # 256 > max_res=128 with min_res <= max_res, so this is the only failing rule.
        message = ConstrainResolution.validate_inputs(64, 128, 256, STRICT)
        assert isinstance(message, str)
        assert "larger than max_res" in message

    def test_min_res_mode_tolerates_multiple_of_above_max_res(self):
        # Min-res mode bumps dimensions up to the next multiple (64x128 input,
        # multiple_of=256 -> 256x256), so a large multiple_of is valid there.
        assert ConstrainResolution.validate_inputs(64, 128, 256, MIN) is True

    def test_strict_mode_accepts_valid_combination(self):
        assert ConstrainResolution.validate_inputs(704, 1280, 32, STRICT) is True

    @pytest.mark.parametrize(
        "args",
        [
            (704, MAX_RESOLUTION + 1, 2, MIN),
            (MAX_RESOLUTION + 1, MAX_RESOLUTION + 1, 2, MIN),
            (704, 1280, MAX_MULTIPLE_OF + 1, MIN),
        ],
    )
    def test_rejects_out_of_range_values(self, args):
        """Naming an input in validate_inputs makes ComfyUI skip its own
        min/max check for it, so the schema bounds have to be re-asserted here.
        An unbounded max_res would also make the pixel budget meaningless."""
        message = ConstrainResolution.validate_inputs(*args)
        assert isinstance(message, str), f"{args} should have been rejected"
        assert "must be between" in message

    def test_rejects_unknown_constraint_mode(self):
        message = ConstrainResolution.validate_inputs(704, 1280, 2, "TypoMode")
        assert isinstance(message, str)
        assert "constraint_mode" in message

    def test_schema_bounds_match_validate_inputs(self, monkeypatch):
        """The bounds are shared constants precisely so the widget and the
        queue-time check cannot drift apart."""
        captured = TestSchemaContract._capture(monkeypatch)
        ConstrainResolution.define_schema()
        bounds = {name: kwargs for name, kwargs in captured["inputs"]}
        assert bounds["max_res"]["max"] == MAX_RESOLUTION
        assert bounds["min_res"]["max"] == MAX_RESOLUTION
        assert bounds["multiple_of"]["max"] == MAX_MULTIPLE_OF


class TestExtremeRatioCropping:
    def test_very_tall_image_is_cropped_not_distorted(self):
        """A ratio that rounds to 0.0 used to skip the crop branch entirely."""
        image = torch.rand(1, 3000, 1, 3)
        resized, _, out_w, out_h, _, _ = run_node(
            image, multiple_of=32, constraint_mode=STRICT
        )
        assert resized.shape == (1, out_h, out_w, 3)


class TestSchemaContract:
    """conftest mocks comfy_api, so nothing else exercises define_schema().
    Schema drift - an input renamed while execute() was not - would only
    surface as a load failure inside real ComfyUI."""

    @staticmethod
    def _capture(monkeypatch):
        mock_io = sys.modules['comfy_api.latest'].io
        captured = {"inputs": [], "schema": None}

        def make_recorder(bucket):
            def factory(*args, **kwargs):
                bucket.append((args[0] if args else "", kwargs))
                return None
            return factory

        def fake_schema(**kwargs):
            captured["schema"] = kwargs
            return kwargs

        for kind in ("Image", "Mask", "Latent", "Int", "Float", "String", "Combo", "Boolean"):
            namespace = types.SimpleNamespace()
            namespace.Input = make_recorder(captured["inputs"])
            namespace.Output = make_recorder([])
            monkeypatch.setattr(mock_io, kind, namespace, raising=False)
        monkeypatch.setattr(mock_io, "Schema", fake_schema, raising=False)
        return captured

    def test_execute_params_are_all_schema_inputs(self, monkeypatch):
        captured = self._capture(monkeypatch)
        ConstrainResolution.define_schema()

        schema_names = {name for name, _ in captured["inputs"]}
        execute_params = set(inspect.signature(ConstrainResolution.execute).parameters)
        missing = execute_params - schema_names
        assert not missing, f"execute() params missing from define_schema(): {missing}"

    def test_every_input_documents_itself(self, monkeypatch):
        captured = self._capture(monkeypatch)
        ConstrainResolution.define_schema()

        unexplained = [name for name, kwargs in captured["inputs"] if not kwargs.get("tooltip")]
        assert not unexplained, f"schema inputs missing tooltips: {unexplained}"
        assert captured["schema"], "io.Schema(...) was never called"
        assert captured["schema"].get("description")
