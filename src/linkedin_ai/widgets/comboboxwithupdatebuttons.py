from typing import Optional, Union, List

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from .checkablecombobox import CheckableComboBox


class ComboBoxWithUpdateButtons(qtw.QWidget):
    refreshOptions = qtc.pyqtSignal()

    def __init__(
        self,
        initial_options: Optional[List[str]] = None,
        initial_text: Optional[str] = None,
        add_new_button_text: str = "Add New",
        do_add_new_button_text: str = "Add",
        cancel_add_new_button_text: str = "Cancel",
        refresh_button_text: str = "Refresh",
        combo_box_class: Union[qtw.QComboBox, CheckableComboBox] = qtw.QComboBox,
    ):
        super().__init__()

        layout = qtw.QHBoxLayout(self)
        self.combo_box = combo_box_class()
        if initial_options:
            self.add_options(initial_options)
            if initial_text:
                self.combo_box.setCurrentText(initial_text)

        self.add_new_line_edit = qtw.QLineEdit()
        self.do_add_new_button = qtw.QPushButton(do_add_new_button_text)
        self.cancel_add_new_button = qtw.QPushButton(cancel_add_new_button_text)
        self.add_new_line_edit.hide()
        self.do_add_new_button.hide()
        self.cancel_add_new_button.hide()

        self.add_new_button = qtw.QPushButton(add_new_button_text)
        self.refresh_button = qtw.QPushButton(refresh_button_text)

        layout.addWidget(self.combo_box)
        layout.addWidget(self.add_new_line_edit)
        layout.addWidget(self.do_add_new_button)
        layout.addWidget(self.cancel_add_new_button)
        layout.addWidget(self.add_new_button)
        layout.addWidget(self.refresh_button)

        self.refresh_button.clicked.connect(self.refreshOptions.emit)
        self.add_new_button.clicked.connect(self.onAddNewButtonClicked)
        self.do_add_new_button.clicked.connect(self.onDoAddNewButtonClicked)
        self.cancel_add_new_button.clicked.connect(self.onCancelAddNewButtonClicked)

    @qtc.pyqtSlot(list)
    def update_options(self, options):
        self.combo_box.clear()
        self.add_options(options)

    @qtc.pyqtSlot(list)
    def add_options(self, options):
        self.combo_box.addItems(options)

    def onAddNewButtonClicked(self):
        self.add_new_button.hide()
        self.refresh_button.hide()
        self.add_new_line_edit.show()
        self.do_add_new_button.show()
        self.cancel_add_new_button.show()

    def onDoAddNewButtonClicked(self):
        new_option = self.add_new_line_edit.text()
        self.combo_box.addItem(new_option)
        self.combo_box.setCurrentText(new_option)
        self.onCancelAddNewButtonClicked()

    def onCancelAddNewButtonClicked(self):
        self.add_new_line_edit.clear()
        self.add_new_line_edit.hide()
        self.do_add_new_button.hide()
        self.cancel_add_new_button.hide()
        self.add_new_button.show()
        self.refresh_button.show()

    def currentData(self):
        return self.combo_box.currentData()

    def setCurrentData(self, data):
        return self.combo_box.setCurrentData(data)

    def currentText(self):
        return self.combo_box.currentText()

    def setCurrentText(self, text):
        return self.combo_box.setCurrentText(text)
