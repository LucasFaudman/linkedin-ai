from typing import Optional, TypeVar, Type
from pathlib import Path

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

T = TypeVar("T")


class FileSelectWidget(qtw.QWidget):
    fileSelected = qtc.pyqtSignal(object)

    def __init__(
        self,
        initial_path: Optional[Path | str] = None,
        button_text: str = "Select File",
        dialog_title: Optional[str] = None,
        no_selection_text: str = "No File Selected",
        return_as: type = Path,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.return_as = return_as
        self.button_text = button_text
        self.dialog_title = dialog_title or button_text
        self.no_selection_text = no_selection_text

        if initial_path and not isinstance(initial_path, Path):
            initial_path = Path(initial_path).resolve()
        initial_label_text = str(initial_path) if initial_path else self.no_selection_text

        layout = qtw.QHBoxLayout(self)
        self.file_path_label = qtw.QLabel(initial_label_text)
        self.file_select_button = qtw.QPushButton(self.button_text)
        layout.addWidget(self.file_path_label)
        layout.addWidget(self.file_select_button)

        self.file_select_button.clicked.connect(self.onSelectFileButtonClicked)

    def _type_path(self, path: str, return_as: Type[T]) -> T:
        return path if isinstance(path, return_as) else return_as(path)

    @qtc.pyqtSlot()
    def onSelectFileButtonClicked(self) -> None:
        path, _ = qtw.QFileDialog.getOpenFileName(self, "Select File")
        self.file_path_label.setText(path)
        self.fileSelected.emit(self._type_path(path, self.return_as))

    def get_file_path(self) -> Optional[str | Path]:
        path = self.file_path_label.text()
        if path != self.no_selection_text:
            return self._type_path(path, self.return_as)
        return None
