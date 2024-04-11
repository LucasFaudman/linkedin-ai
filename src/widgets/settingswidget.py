from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from typing import Optional
from pathlib import Path
from json import load as json_load, dump as json_dump

from .fileselectwidget import FileSelectWidget
from .comboboxwithupdatebuttons import ComboBoxWithUpdateButtons


class SettingsWidget(qtw.QWidget):
    settingsUpdated = qtc.pyqtSignal(dict)

    DEFAULT_CONFIG = {
        'resume_path': "./resume.txt",
        'default_cover_letter_path': None,
        'job_app_db_path': "./jobs.db",
        "auto_login": True,
        'li_username': None,
        'li_password': None,
        'li_auto_login': True,
        'api_key': None,
        'model': 'gpt-4',
        'assistant_id': None,
        'thread_id': None,
        'ai_db_path': './ai.db',
        'webdriver_path': "./chromedriver",
        'user_agent': None,
        'proxy': None
    }

    def __init__(self, config_path: Path, **kwargs) -> None:
        super().__init__(**kwargs)

        self.config_path = config_path
        if self.config_path.exists():
            with self.config_path.open('r') as f:
                self.config = json_load(f)
        else:
            self.config = self.DEFAULT_CONFIG.copy()

        layout = qtw.QVBoxLayout(self)

        # User settings
        user_settings_groupbox = qtw.QGroupBox('User Settings')
        user_settings_layout = qtw.QFormLayout(user_settings_groupbox)
        layout.addWidget(user_settings_groupbox)

        self.resume_path_file_select = FileSelectWidget(
            initial_path=self.config['resume_path'], button_text='Select Resume')
        user_settings_layout.addRow(
            'Resume Path:', self.resume_path_file_select)
        
        self.default_cover_letter_path_file_select = FileSelectWidget(
            initial_path=self.config['default_cover_letter_path'], button_text='Select Default Cover Letter')
        user_settings_layout.addRow(
            'Default Cover Letter Path:', self.default_cover_letter_path_file_select)

        self.cover_letter_action_combo_box = qtw.QComboBox()
        cover_letter_actions = {
            'skip': 'Skip Cover Letters (saves application and sets job status to "needs cover letter")',
            'default': 'Use Default Cover Letter for all jobs',
            'generate': 'Generate Custom Cover Letter for each job with AI'
        }
        for action, description in cover_letter_actions.items():
            self.cover_letter_action_combo_box.addItem(description, action)
        self.cover_letter_action_combo_box.setCurrentText(cover_letter_actions[self.config['cover_letter_action']])
        user_settings_layout.addRow('Cover Letter Action:', self.cover_letter_action_combo_box) 

        self.job_app_db_file_select = FileSelectWidget(
            initial_path=self.config['job_app_db_path'], button_text='Select Job Application DB Path')
        user_settings_layout.addRow(
            'Job Application DB Path:', self.job_app_db_file_select)

        # LinkedIn settings
        linkedin_settings_groupbox = qtw.QGroupBox('LinkedIn Settings')
        linkedin_settings_layout = qtw.QFormLayout(linkedin_settings_groupbox)
        layout.addWidget(linkedin_settings_groupbox)

        self.li_username_line_edit = qtw.QLineEdit()
        self.li_username_line_edit.setText(self.config['li_username'])
        linkedin_settings_layout.addRow(
            'LinkedIn Username:', self.li_username_line_edit)

        self.li_password_line_edit = qtw.QLineEdit()
        self.li_password_line_edit.setEchoMode(qtw.QLineEdit.Password)
        self.li_password_line_edit.setText(self.config['li_password'])
        linkedin_settings_layout.addRow(
            'LinkedIn Password:', self.li_password_line_edit)

        self.li_auto_login_checkbox = qtw.QCheckBox('Automatically Login')
        self.li_auto_login_checkbox.setChecked(self.config['li_auto_login'])
        linkedin_settings_layout.addRow(
            'Automatically Login:', self.li_auto_login_checkbox)

        # OpenAI settings
        ai_settings_groupbox = qtw.QGroupBox('OpenAI Settings')
        ai_settings_layout = qtw.QFormLayout(ai_settings_groupbox)
        layout.addWidget(ai_settings_groupbox)

        self.api_key_line_edit = qtw.QLineEdit()
        self.api_key_line_edit.setText(self.config['api_key'])
        ai_settings_layout.addRow('API Key:', self.api_key_line_edit)

        model_inital_options = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-preview']
        if self.config['model'] not in model_inital_options:
            model_inital_options.append(self.config['model'])
        self.model_combo_box = ComboBoxWithUpdateButtons(
            initial_options=model_inital_options, initial_text=self.config['model'])
        ai_settings_layout.addRow('Model:', self.model_combo_box)

        self.assistant_id_combo_box = ComboBoxWithUpdateButtons(
            initial_options=[self.config['assistant_id']
                             ], initial_text=self.config['assistant_id']
        )
        ai_settings_layout.addRow('Assistant ID:', self.assistant_id_combo_box)

        self.thread_id_combo_box = ComboBoxWithUpdateButtons(
            initial_options=[self.config['thread_id']
                             ], initial_text=self.config['thread_id']
        )
        ai_settings_layout.addRow('Thread ID:', self.thread_id_combo_box)

        self.ai_db_file_select = FileSelectWidget(
            initial_path=self.config['ai_db_path'], button_text='Select AI DB Path')
        ai_settings_layout.addRow('AI DB Path:', self.ai_db_file_select)

        # Selenium settings
        selenium_settings_groupbox = qtw.QGroupBox('Selenium Settings')
        selenium_settings_layout = qtw.QFormLayout(selenium_settings_groupbox)
        layout.addWidget(selenium_settings_groupbox)

        self.webdriver_path_file_select = FileSelectWidget(
            initial_path=self.config['webdriver_path'], button_text='Select Webdriver Path')
        selenium_settings_layout.addRow(
            'Webdriver Path:', self.webdriver_path_file_select)
        
        self.user_agent_line_edit = qtw.QLineEdit()
        self.user_agent_line_edit.setText(self.config['user_agent'])
        selenium_settings_layout.addRow(
            'User Agent:', self.user_agent_line_edit)
        
        self.proxy_line_edit = qtw.QLineEdit()
        self.proxy_line_edit.setText(self.config['proxy'])
        selenium_settings_layout.addRow(
            'Proxy:', self.proxy_line_edit)

        # Update button
        self.update_button = qtw.QPushButton('Update Settings')
        self.update_button.clicked.connect(self.onUpdatedSettingsClicked)
        layout.addWidget(self.update_button)

    def get_settings(self) -> dict[str, Optional[str | Path | bool]]:
        settings = {
            'resume_path': self.resume_path_file_select.get_file_path(),
            'default_cover_letter_path': self.default_cover_letter_path_file_select.get_file_path(),
            "cover_letter_action": self.cover_letter_action_combo_box.currentData(),
            'job_app_db_path': self.job_app_db_file_select.get_file_path(),
            'li_username': self.li_username_line_edit.text(),
            'li_password': self.li_password_line_edit.text(),
            'li_auto_login': self.li_auto_login_checkbox.isChecked(),
            'api_key': self.api_key_line_edit.text(),
            'model': self.model_combo_box.currentText(),
            'assistant_id': self.assistant_id_combo_box.currentText(),
            'thread_id': self.thread_id_combo_box.currentText(),
            'ai_db_path': self.ai_db_file_select.get_file_path(),
            'webdriver_path': self.webdriver_path_file_select.get_file_path(),
            'user_agent': self.user_agent_line_edit.text(),
            'proxy': self.proxy_line_edit.text()
        }
        return settings

    @qtc.pyqtSlot()
    def onUpdatedSettingsClicked(self) -> None:
        settings = self.get_settings()
        with open(self.config_path, 'w') as f:
            json_dump(settings, f, indent=4)
        self.settingsUpdated.emit(settings)
