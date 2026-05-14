"""Phase 1 shell for the MutaBoard workspace."""

from __future__ import annotations

from ._shared import BaseWorkspace, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget, get_theme_palette
from .mutaboard_model import MutaBoardModel


class MutaBoardWorkspace(BaseWorkspace):
    """Workspace shell for the mixed-entity MutaBoard mode."""

    workspace_id = "mutaboard"
    workspace_title = "Мутаборд"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = MutaBoardModel()
        self.search_input.setPlaceholderText("Поиск по мутаборду")
        self._build_phase_one_shell()
        self.refresh()

    def _build_phase_one_shell(self) -> None:
        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hero = QFrame(content)
        hero.setObjectName("MutaBoardHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(10)

        hero_title = QLabel("Мутаборд")
        hero_title.setObjectName("MutaBoardHeroTitle")
        hero_layout.addWidget(hero_title)

        hero_body = QLabel(
            "Phase 1 подключает новый режим в оболочку приложения. "
            "Следующие этапы добавят unified model, board-колонки, inspector и mutation actions."
        )
        hero_body.setObjectName("MutaBoardHeroBody")
        hero_body.setWordWrap(True)
        hero_layout.addWidget(hero_body)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        for text in ("Tasks", "Ideas", "Objects", "Phase 1"):
            chip = QLabel(text)
            chip.setObjectName("MutaBoardPhaseChip")
            chips_row.addWidget(chip)
        chips_row.addStretch(1)
        hero_layout.addLayout(chips_row)
        layout.addWidget(hero)

        next_steps = QFrame(content)
        next_steps.setObjectName("MutaBoardSteps")
        next_steps_layout = QVBoxLayout(next_steps)
        next_steps_layout.setContentsMargins(18, 16, 18, 16)
        next_steps_layout.setSpacing(6)

        steps_title = QLabel("Следующие шаги")
        steps_title.setObjectName("MutaBoardSectionTitle")
        next_steps_layout.addWidget(steps_title)

        for text in (
            "Собрать unified card model для задач, идей и объектов.",
            "Добавить board view с lifecycle-колонками.",
            "Подключить inspector и actions для мутаций сущностей.",
        ):
            label = QLabel(f"• {text}")
            label.setObjectName("MutaBoardStepText")
            label.setWordWrap(True)
            next_steps_layout.addWidget(label)

        layout.addWidget(next_steps)
        layout.addStretch(1)
        self.set_content(content)
        self._apply_mutaboard_style()

    def set_theme_mode(self, theme_mode: str) -> None:
        super().set_theme_mode(theme_mode)
        self._apply_mutaboard_style()

    def apply_query(self, query: str) -> None:
        self._refresh_status()

    def apply_filters(self, filters: dict[str, object]) -> None:
        self._refresh_status()

    def refresh(self) -> None:
        self._model.reload()
        self._refresh_status()

    def _refresh_status(self) -> None:
        filters = self.get_filters()
        cards = self._model.filtered_cards(
            query=self.search_input.text(),
            entity_kind=filters.get("entity_kind") if isinstance(filters.get("entity_kind"), str) else None,
            project_id=filters.get("project_id") if isinstance(filters.get("project_id"), int) else None,
            actionable_only=bool(filters.get("actionable_only")),
            linked_only=filters.get("linked_only") if isinstance(filters.get("linked_only"), bool) else None,
        )
        total_count = len(self._model.cards())
        visible_count = len(cards)
        if self.search_input.text().strip() or filters:
            self.set_status(f"Мутаборд: карточек {visible_count} из {total_count}.")
            return
        self.set_status(f"Мутаборд: карточек {total_count}.")

    def _apply_mutaboard_style(self) -> None:
        palette = get_theme_palette(self._theme_mode)
        self.content_host.setStyleSheet(
            f"""
            QFrame#MutaBoardHero,
            QFrame#MutaBoardSteps {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 14px;
            }}
            QLabel#MutaBoardHeroTitle,
            QLabel#MutaBoardSectionTitle {{
                color: {palette.text};
                font-size: 18px;
                font-weight: 700;
            }}
            QLabel#MutaBoardHeroBody,
            QLabel#MutaBoardStepText {{
                color: {palette.dim_text};
                font-size: 12px;
            }}
            QLabel#MutaBoardPhaseChip {{
                color: {palette.selection_text};
                background: {palette.selection_bg};
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            """
        )
