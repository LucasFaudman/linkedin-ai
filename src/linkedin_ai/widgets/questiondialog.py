from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from ..models import Question


class QuestionDialog(qtw.QDialog):
    questionAnswered = qtc.pyqtSignal(Question)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Answer Question")
        self.setModal(True)
        self.label = qtw.QLabel("Question:")
        self.label.setWordWrap(True)
        layout = qtw.QVBoxLayout(self)
        layout.addWidget(self.label)

        self.answer_text_edit = qtw.QTextEdit()
        self.answer_combo_box = qtw.QComboBox()
        layout.addWidget(self.answer_text_edit)
        layout.addWidget(self.answer_combo_box)

        self.button_box = qtw.QDialogButtonBox(qtw.QDialogButtonBox.Ok | qtw.QDialogButtonBox.Cancel)
        layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.question = None
        self.is_text_input = None

    def ask_question(self, question: Question) -> None:
        self.label.setText(question.question)
        if is_text_input := question.choices is None:
            self.answer_combo_box.hide()
            self.answer_text_edit.show()
            self.answer_text_edit.clear()
            if question.answer:
                self.answer_text_edit.setText(question.answer)
        else:
            self.answer_text_edit.hide()
            self.answer_combo_box.show()
            self.answer_combo_box.clear()
            self.answer_combo_box.addItems(question.choices)
            if question.answer:
                self.answer_combo_box.setCurrentText(question.answer)

        self.question = question
        self.is_text_input = is_text_input

        self.show()
        while self.isVisible():  # Wait for the dialog to be closed
            qtc.QCoreApplication.processEvents()

    def get_answered_question(self) -> Question:
        if self.is_text_input:
            self.question.answer = self.answer_text_edit.toPlainText().strip()
        else:
            self.question.answer = self.answer_combo_box.currentText()

        self.questionAnswered.emit(self.question)
        return self.question
