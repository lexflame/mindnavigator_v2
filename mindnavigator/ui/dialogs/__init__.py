from .attach_file_select_nav import AttachFileSelectNav
from .base_dialog import MNBaseDialog
from .entity_picker_dialog import ChipItem, EntityPickerDialog
from .map_label_edit_dialog import MapLabelEditDialog
from .purchase_add_dialog import PurchaseAddByUrlDialog, PurchaseAddResult
from .purchase_compare_dialog import PurchaseCompareDialog
from .purchase_edit_dialog import PurchaseEditDialog

__all__ = [
    "AttachFileSelectNav",
    "ChipItem",
    "EntityPickerDialog",
    "MNBaseDialog",
    "MapLabelEditDialog",
    "PurchaseAddByUrlDialog",
    "PurchaseAddResult",
    "PurchaseCompareDialog",
    "PurchaseEditDialog",
]
"""Диалоги интерфейса MindNavigator.

Входные данные:
    Нет. Пакет организует модальные окна приложения.

Выходные данные:
    Доступ к подмодулям диалогов.
"""
