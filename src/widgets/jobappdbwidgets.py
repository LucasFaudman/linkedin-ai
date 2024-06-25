from typing import Union

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from pydantic import BaseModel

from .modeltablewidget import ModelTableWidget


class JobsTableWidget(ModelTableWidget):
    def transform_item_for_table(self, item: Union[BaseModel, dict]) -> dict:
        if isinstance(item, BaseModel):
            item = item.model_dump()
            if company := item["company"]:
                item["company"] = company.get("name")
            if hiring_manager := item.get("hiring_manager"):
                item["hiring_manager"] = hiring_manager.get("name")
            item["easy_apply"] = bool(item.get("easy_apply"))
        return item


class JobAppDBInteractionWidget(qtw.QWidget):
    getJobsFromDB = qtc.pyqtSignal()
    applyJobs = qtc.pyqtSignal(list)
    scrapeJobs = qtc.pyqtSignal(list)
    openJobs = qtc.pyqtSignal(list)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        layout = qtw.QVBoxLayout(self)

        self.refresh_button = qtw.QPushButton("Refresh Jobs from DB")
        self.refresh_button.clicked.connect(self.getJobsFromDB.emit)
        self.jobs_table_widget = JobsTableWidget([], resize_columns=False)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.jobs_table_widget)

        self.button_layout = qtw.QHBoxLayout()
        self.apply_jobs_button = qtw.QPushButton("Apply to Selected Jobs")
        self.scrape_jobs_button = qtw.QPushButton("Scrape and Update Selected Jobs")
        self.open_jobs_button = qtw.QPushButton("Open Selected Jobs")
        self.apply_jobs_button.clicked.connect(self.apply_to_selected_jobs)
        self.scrape_jobs_button.clicked.connect(self.scrape_selected_jobs)
        self.open_jobs_button.clicked.connect(self.open_selected_jobs)

        self.button_layout.addWidget(self.apply_jobs_button)
        self.button_layout.addWidget(self.scrape_jobs_button)
        self.button_layout.addWidget(self.open_jobs_button)
        layout.addLayout(self.button_layout)

    @qtc.pyqtSlot(list)
    def update_jobs(self, data_list) -> None:
        self.jobs_table_widget.update_table(data_list)

    def apply_to_selected_jobs(self) -> None:
        selected_jobs = self.jobs_table_widget.get_selected_rows()
        self.applyJobs.emit(selected_jobs)

    def scrape_selected_jobs(self) -> None:
        selected_jobs = self.jobs_table_widget.get_selected_rows()
        self.scrapeJobs.emit(selected_jobs)

    def open_selected_jobs(self) -> None:
        selected_jobs = self.jobs_table_widget.get_selected_rows()
        self.openJobs.emit(selected_jobs)


class QuestionDBInteractionWidget(qtw.QWidget):
    getQuestionsFromDB = qtc.pyqtSignal()
    editQuestions = qtc.pyqtSignal(list)
    deleteQuestions = qtc.pyqtSignal(list)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        layout = qtw.QVBoxLayout(self)

        self.refresh_button = qtw.QPushButton("Refresh Questions from DB")
        self.refresh_button.clicked.connect(self.getQuestionsFromDB.emit)
        self.questions_table_widget = ModelTableWidget([], resize_columns=False)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.questions_table_widget)

        self.button_layout = qtw.QHBoxLayout()
        self.edit_questions_button = qtw.QPushButton("Edit Selected Questions")
        self.delete_questions = qtw.QPushButton("Delete Selected Questions")
        self.edit_questions_button.clicked.connect(self.edit_selected_questions)
        self.delete_questions.clicked.connect(self.delete_selected_questions)

        self.button_layout.addWidget(self.edit_questions_button)
        self.button_layout.addWidget(self.delete_questions)
        layout.addLayout(self.button_layout)

    @qtc.pyqtSlot(list)
    def update_questions(self, data_list) -> None:
        self.questions_table_widget.update_table(data_list)

    def edit_selected_questions(self) -> None:
        selected_questions = self.questions_table_widget.get_selected_rows()
        self.editQuestions.emit(selected_questions)

    def delete_selected_questions(self) -> None:
        selected_questions = self.questions_table_widget.get_selected_rows()
        self.deleteQuestions.emit(selected_questions)
