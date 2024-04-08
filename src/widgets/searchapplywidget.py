from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from .checkablecombobox import CheckableComboBox
from .jobappdbwidgets import JobsTableWidget
from typing import Optional


class SearchFiltersWidget(qtw.QWidget):
    valueChanged = qtc.pyqtSignal(dict)
    getFilterOptions = qtc.pyqtSignal(str)

    def __init__(self, input_dict: dict, **kwargs) -> None:
        super().__init__(**kwargs)

        self.input_dict = {
            'Distance': ('radio', ['5 miles', '10 miles', '25 miles', '50 miles', '100 miles']),
            **input_dict
        }
        self.search_term = 'Python Automation'
        self.location = 'Seattle, WA'
        self.setup_ui()

    def setup_ui(self) -> None:
        self.input_widgets: dict[str, qtw.QWidget] = {}
        if (layout := self.layout()) is None:
            layout = qtw.QFormLayout(self)

        #layout.addWidget(qtw.QLabel('Search Filters'))

        self.search_input = qtw.QLineEdit()
        self.search_input.setPlaceholderText(
            'Search Term: ie. "Python Automation"')
        if self.search_term:
            self.search_input.setText(self.search_term)
        self.search_input.textChanged.connect(self.emit_values)
        self.search_input.setSizePolicy(
            qtw.QSizePolicy.Expanding, qtw.QSizePolicy.Fixed)
        layout.addRow('Search Term', self.search_input)

        self.location_input = qtw.QLineEdit()
        self.location_input.setPlaceholderText(
            'Location: ie. "San Francisco, CA"')
        if self.location:
            self.location_input.setText(self.location)
        self.location_input.textChanged.connect(self.emit_values)
        self.location_input.setSizePolicy(
            qtw.QSizePolicy.Expanding, qtw.QSizePolicy.Fixed)
        layout.addRow('Location', self.location_input)

        self.update_filters_button = qtw.QPushButton('Update Filters')
        self.update_filters_button.clicked.connect(self.get_filter_options)
        self.update_filters_button.setSizePolicy(
            qtw.QSizePolicy.Expanding, qtw.QSizePolicy.Fixed)
        layout.addWidget(self.update_filters_button)

        # layout.addWidget(qtw.QLabel('Search Filters'))
        for key, (input_type, choices) in self.input_dict.items():
            label = qtw.QLabel(text=key)
            if input_type == 'text':
                widget = qtw.QLineEdit()
                widget.textChanged.connect(self.emit_values)
            elif input_type == 'toggle':
                widget = qtw.QCheckBox()
                widget.stateChanged.connect(self.emit_values)
            elif input_type == 'spinbox':
                widget = qtw.QSpinBox()
                widget.valueChanged.connect(self.emit_values)
            elif input_type == 'radio':
                widget = qtw.QComboBox()
                widget.addItems(choices)
                widget.setCurrentIndex(-1)
                widget.currentIndexChanged.connect(self.emit_values)
            elif input_type == 'checkbox':
                widget = CheckableComboBox()
                widget.addItems(choices)
                widget.dataChanged.connect(self.emit_values)

            else:
                raise ValueError(f"Unsupported input type: {input_type}")

            widget.setSizePolicy(qtw.QSizePolicy.Expanding,
                                 qtw.QSizePolicy.Fixed)
            layout.addRow(label, widget)
            self.input_widgets[key] = widget

    def get_set_filters(self) -> dict[str, Optional[str]]:
        self.search_term = self.search_input.text()
        self.location = self.location_input.text()
        values: dict[str, Optional[str]] = {
            'search_term': self.search_term,
            'location': self.location,
        }
        for key, widget in self.input_widgets.items():
            if isinstance(widget, qtw.QLineEdit):
                value = widget.text()
            elif isinstance(widget, qtw.QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, qtw.QSpinBox):
                value = widget.value()
            elif isinstance(widget, CheckableComboBox):
                value = widget.currentData()
            elif isinstance(widget, qtw.QComboBox):
                value = widget.currentText() if widget.currentIndex() != -1 else None

            if value is not None:
                values[key] = value

        return values

    def emit_values(self) -> None:
        self.valueChanged.emit(self.get_set_filters())

    def get_filter_options(self) -> None:
        self.getFilterOptions.emit(self.search_input.text())

    @qtc.pyqtSlot(dict)
    def update_options(self, new_input_dict: dict) -> None:
        self.input_dict = {
            'Distance': ('radio', ['5 miles', '10 miles', '25 miles', '50 miles', '100 miles']),
            **new_input_dict
        }
        self.clear_layout()
        self.setup_ui()

    def clear_layout(self) -> None:
        if (layout := self.layout()) is not None:
            for i in reversed(range(layout.count())):
                layout.itemAt(i).widget().setParent(None)


class SearchAndApplyWidget(qtw.QWidget):
    newSearch = qtc.pyqtSignal(dict)
    applyJobs = qtc.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        layout = qtw.QVBoxLayout(self)
        splitter = qtw.QSplitter(qtc.Qt.Horizontal, self)
        layout.addWidget(splitter)

        filters_search_button_layout = qtw.QVBoxLayout()
        self.search_filters_widget = SearchFiltersWidget({})
        filters_search_button_layout.addWidget(self.search_filters_widget)

        self.search_jobs_button = qtw.QPushButton('Search for Jobs')
        self.search_jobs_button.clicked.connect(self.search_jobs)
        filters_search_button_layout.addWidget(self.search_jobs_button)

        select_apply_layout = qtw.QVBoxLayout()
        self.jobs_table_widget = JobsTableWidget(
            [], resize_columns=["title", "company", "location"])
        select_apply_layout.addWidget(self.jobs_table_widget)

        interaction_form = qtw.QHBoxLayout()
        self.ask_when_needed_checkbox = qtw.QCheckBox(
            'Ask for Answers When Needed')
        self.ask_when_needed_checkbox.setChecked(True)
        self.verify_ai_answers_checkbox = qtw.QCheckBox(
            'Verify AI Provided Answers')
        self.verify_ai_answers_checkbox.setChecked(True)
        interaction_form.addWidget(self.ask_when_needed_checkbox)
        interaction_form.addWidget(self.verify_ai_answers_checkbox)
        select_apply_layout.addLayout(interaction_form)

        self.apply_jobs_button = qtw.QPushButton('Apply to Selected Jobs')
        self.apply_jobs_button.clicked.connect(self.apply_to_selected_jobs)
        select_apply_layout.addWidget(self.apply_jobs_button)

        #self.search_filters_widget.setSizePolicy(
        #    qtw.QSizePolicy.Expanding, qtw.QSizePolicy.Expanding)
        #self.jobs_table_widget.setSizePolicy(
        #    qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Expanding)
        
        filters_groupbox = qtw.QGroupBox('Search for Jobs')
        filters_groupbox.setLayout(filters_search_button_layout)
        splitter.addWidget(filters_groupbox)
        select_apply_groupbox = qtw.QGroupBox('Apply to Jobs')
        select_apply_groupbox.setLayout(select_apply_layout)
        splitter.addWidget(select_apply_groupbox)
        splitter.setSizes([1, 3])




    @qtc.pyqtSlot(list)
    def update_filters(self, new_input_dict: dict) -> None:
        self.search_filters_widget.update_options(new_input_dict)

    @qtc.pyqtSlot(list)
    def update_jobs(self, data_list: list) -> None:
        self.jobs_table_widget.update_table(data_list)

    def search_jobs(self) -> None:
        self.newSearch.emit(self.search_filters_widget.get_set_filters())

    def apply_to_selected_jobs(self) -> None:
        selected_jobs = self.jobs_table_widget.get_selected_rows()
        self.applyJobs.emit(selected_jobs)
