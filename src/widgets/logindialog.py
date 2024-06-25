from typing import Optional

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc


class LoginDialog(qtw.QDialog):
    loginAttempted = qtc.pyqtSignal(str, str)
    loginDone = qtc.pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("LinkedIn AI is starting up...")
        self.setGeometry(100, 100, 400, 200)
        self.setModal(True)

        self.overlay_widget = qtw.QWidget(self)
        self.overlay_widget.setGeometry(self.geometry())

        layout = qtw.QVBoxLayout()

        self.username_label = qtw.QLabel("Username:")
        self.password_label = qtw.QLabel("Password:")
        self.username_input = qtw.QLineEdit()
        self.password_input = qtw.QLineEdit()
        self.password_input.setEchoMode(qtw.QLineEdit.Password)  # Hide password input

        self.login_button = qtw.QPushButton("Login")
        self.login_button.clicked.connect(self.handle_login)

        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        self.username_label.hide()
        self.username_input.hide()
        self.password_label.hide()
        self.password_input.hide()
        self.login_button.hide()

        self.overlay_text = qtw.QLabel("LinkedIn AI is starting up...")
        self.overlay_text.show()
        self.overlay_button = qtw.QPushButton("Completed Captcha")
        self.overlay_button.hide()
        self.overlay_button.clicked.connect(self.onLoginSuccess)

        layout.addWidget(self.overlay_text)
        layout.addWidget(self.overlay_button)

        self.setLayout(layout)

    def show_overlay(self, overlay_text, button_text=None, window_title=None) -> None:
        self.username_label.hide()
        self.username_input.hide()
        self.password_label.hide()
        self.password_input.hide()
        self.login_button.hide()

        self.overlay_text.setText(overlay_text)
        self.overlay_text.show()
        if button_text:
            self.overlay_button.setText(button_text)
            self.overlay_button.show()
        if window_title:
            self.setWindowTitle(window_title)
        else:
            self.setWindowTitle(overlay_text)

    def show_initializing_and_accept(self) -> None:
        self.show_overlay(
            overlay_text="Login successful. Initializing...",
            window_title="Initializing...",
        )
        self.accept()
        self.loginDone.emit()

    def onLoginReady(self) -> None:
        self.setWindowTitle("Login to LinkedIn")
        self.overlay_text.hide()
        self.overlay_button.hide()
        self.username_label.show()
        self.username_input.show()
        self.password_label.show()
        self.password_input.show()
        self.login_button.show()
        self.login_button.setEnabled(True)

    def onLoginResult(self, success) -> None:
        if success:
            self.show_initializing_and_accept()
        else:
            self.show_overlay(
                overlay_text='Captcha required. Please complete the captcha and click "Completed Captcha" to continue.',
                button_text="Completed Captcha",
                window_title="Captcha Required",
            )

    def onLoginSuccess(self) -> None:
        self.show_initializing_and_accept()

    def handle_login(self) -> None:
        self.login_button.setEnabled(False)
        self.show_overlay("Attempting to log in...")
        username = self.username_input.text()
        password = self.password_input.text()
        self.loginAttempted.emit(username, password)

    def set_texts(self, username: Optional[str], password: Optional[str]) -> None:
        self.username_input.setText(username)
        self.password_input.setText(password)

    def auto_login(self, username: str, password: str) -> None:
        self.show()
        self.set_texts(username, password)
        self.handle_login()
