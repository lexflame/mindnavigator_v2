from mindnavigator.ui.styles import build_calendar_popup_stylesheet, get_theme_palette


def test_calendar_popup_stylesheet_uses_theme_palette() -> None:
    palette = get_theme_palette("dark")
    stylesheet = build_calendar_popup_stylesheet("dark")

    assert "QCalendarWidget" in stylesheet
    assert palette.panel_bg in stylesheet
    assert palette.input_alt_bg in stylesheet
    assert palette.accent in stylesheet
