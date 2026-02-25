from __future__ import annotations

from mindnavigator.ui.animations import (
    DialogAppearAnimationConfig,
    WidthExpandAnimationConfig,
    normalize_duration_ms,
    normalize_width_bounds,
)


def test_normalize_width_bounds_clamps_and_orders() -> None:
    collapsed, expanded = normalize_width_bounds(-10, 5)
    assert collapsed == 1
    assert expanded == 5

    collapsed, expanded = normalize_width_bounds(220, 80)
    assert collapsed == 220
    assert expanded == 220


def test_normalize_duration_ms_clamps_minimum() -> None:
    assert normalize_duration_ms(-1) == 1
    assert normalize_duration_ms(0) == 1
    assert normalize_duration_ms(120) == 120


def test_width_expand_config_normalized() -> None:
    config = WidthExpandAnimationConfig(collapsed_width=0, expanded_width=10, duration_ms=0).normalized()
    assert config.collapsed_width == 1
    assert config.expanded_width == 10
    assert config.duration_ms == 1


def test_dialog_appear_config_normalized() -> None:
    config = DialogAppearAnimationConfig(
        duration_ms=0,
        offset_px=-20,
        start_opacity=-1.0,
        end_opacity=4.0,
    ).normalized()
    assert config.duration_ms == 1
    assert config.offset_px == 0
    assert config.start_opacity == 0.0
    assert config.end_opacity == 1.0
