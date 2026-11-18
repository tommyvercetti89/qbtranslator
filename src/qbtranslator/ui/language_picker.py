"""Searchable target language picker with accent-insensitive matching."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from qbtranslator.core.langs import filter_target_languages
from qbtranslator.i18n import t


class LanguagePickerDialog(QDialog):
    def __init__(self, parent, current_code: str = "", ui_lang: str = "tr") -> None:
        super().__init__(parent)
        self.setWindowTitle(t("language_picker.title"))
        self.setModal(True)
        self.resize(380, 480)
        self._ui_lang = ui_lang
        self._selected_code = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText(t("language_picker.search"))
        self.search.textChanged.connect(self._reload)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemDoubleClicked.connect(lambda _item: self._accept_selected())
        self.list.itemActivated.connect(lambda _item: self._accept_selected())
        layout.addWidget(self.list, 1)

        self.count = QLabel("")
        self.count.setObjectName("Muted")
        layout.addWidget(self.count)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(t("common.cancel"))
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        self.ok_button = QPushButton(t("common.save"))
        self.ok_button.setObjectName("Accent")
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self._accept_selected)
        buttons.addWidget(self.ok_button)
        layout.addLayout(buttons)

        self.search.returnPressed.connect(self._accept_selected)
        self.list.currentRowChanged.connect(
            lambda row: self.ok_button.setEnabled(row >= 0)
        )
        self._reload()
        if current_code:
            for index in range(self.list.count()):
                code = self.list.item(index).data(Qt.UserRole)
                if code == current_code:
                    self.list.setCurrentRow(index)
                    self.list.scrollToItem(self.list.item(index))
                    break
        self.search.setFocus()

    @property
    def selected_code(self) -> str:
        return self._selected_code

    def _reload(self) -> None:
        self.list.clear()
        results = filter_target_languages(self.search.text(), self._ui_lang)
        for label, code in results:
            item = _make_item(label, code)
            self.list.addItem(item)
        self.count.setText(t("language_picker.count", count=len(results)))
        self.ok_button.setEnabled(bool(results))

    def _accept_selected(self) -> None:
        item = self.list.currentItem()
        if item is None and self.list.count():
            item = self.list.item(0)
        if item is None:
            return
        self._selected_code = str(item.data(Qt.UserRole) or "")
        if self._selected_code:
            self.accept()


def _make_item(label: str, code: str):
    from PySide6.QtWidgets import QListWidgetItem

    item = QListWidgetItem(label)
    item.setData(Qt.UserRole, code)
    return item
