from typing import Optional, List, Iterator
from pathlib import Path
from functools import wraps
from argparse import ArgumentParser

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

from .widgets import (
    LoginDialog,
    QuestionDialog,
    SearchAndApplyWidget,
    JobAppDBInteractionWidget,
    QuestionDBInteractionWidget,
    SettingsWidget,
)
from .liautomator import LinkedInAutomator, sleep
from .models import Job, Question
from .jobai import AIError
from .core.aimanager import Assistant, Thread, Run, Message


def thread_safe_dbs(func):
    """
    Decorator to ensure that the database connections are closed after the function is called.
    Prevents errors from using an SQLite object in a different thread than it was created and
    prevents the databases from being locked by multiple threads.
    """

    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        rval = None
        try:
            # Init the databases before calling the function
            instance.init_dbs()
            rval = func(instance, *args, **kwargs)
        except Exception as e:
            print(f"thread_safe_dbs caught: {e}")
        finally:
            # Finally ensures dbs are closed even if an exception is raised
            instance.close_dbs()
        return rval

    return wrapper


class LinkedInAutomatorQObject(LinkedInAutomator, qtc.QObject):
    """
    PyQt5 compatible LinkedInAutomator QObject subclass that emits signals for PyQt5 GUI interaction.

    Methods/generators defined in LinkedInAutomator are intercepted and PyQt5 signals are emitted
    before returning/yielding the result.

    All methods that interact with the database(s) are wrapped with the @thread_safe_dbs decorator
    to ensure that the database connections are closed to prevent SQLite errors.

    This allows this class to be used in a separate thread to avoid blocking the main (GUI) thread.
    """

    # Signals
    scraperInitialized = qtc.pyqtSignal()
    aiAndDBsInitialized = qtc.pyqtSignal()
    loginReady = qtc.pyqtSignal()
    loginResult = qtc.pyqtSignal(bool)
    getFilterOptionsResult = qtc.pyqtSignal(dict)
    getCollectionsResult = qtc.pyqtSignal(dict)
    getJobsFromDBResult = qtc.pyqtSignal(list)
    getQuestionsFromDBResult = qtc.pyqtSignal(list)
    newJob = qtc.pyqtSignal(Job)
    openedJob = qtc.pyqtSignal(Job)
    updatedJob = qtc.pyqtSignal(Job)
    appliedJob = qtc.pyqtSignal(Job)
    searchComplete = qtc.pyqtSignal(list)
    applyingComplete = qtc.pyqtSignal(int, int)
    newQuestion = qtc.pyqtSignal(Question)
    updatedQuestion = qtc.pyqtSignal(Question)
    deletedQuestion = qtc.pyqtSignal(Question)
    answerNeeded = qtc.pyqtSignal(Question)

    def __init__(self, *args, ask_when_answer_needed=False, verify_ai_answers=False, **kwargs):
        self.ask_when_answer_needed = ask_when_answer_needed
        self.verify_ai_answers = verify_ai_answers
        self.last_question = None

        # Initalize self as a PyQt5 QObject then as LinkedInAutomator
        qtc.QObject.__init__(self)
        LinkedInAutomator.__init__(self, *args, **kwargs)

    @qtc.pyqtSlot()
    def init_scraper(self):
        """Initalize the SouperScraper. Emits signal when the scaper is ready."""
        LinkedInAutomator.init_scraper(self)
        self.scraperInitialized.emit()

    @qtc.pyqtSlot()
    def init_dbs(self):
        """Initalize the databases. Emits signal when the databases are ready."""
        LinkedInAutomator.init_dbs(self)
        self.aiAndDBsInitialized.emit()

    @qtc.pyqtSlot()
    def teardown(self):
        self.close_scraper()
        self.close_dbs()

    @qtc.pyqtSlot()
    def goto_login(self):
        """Go to the LinkedIn login page. Emits signal when ready for login input."""
        LinkedInAutomator.goto_login(self)
        self.loginReady.emit()

    @qtc.pyqtSlot(str, str)
    def login(self, li_username, li_password):
        """Login to LinkedIn with the given username and password. Emits signal with login result."""
        result = LinkedInAutomator.login(self, li_username, li_password)
        self.loginResult.emit(result)

    @qtc.pyqtSlot(str)
    def get_filter_options(self, search_term: str):
        """Get filter options for a job search. Emits signals when starting and with the filter options."""
        filters = LinkedInAutomator.get_filter_options(self, search_term)
        self.getFilterOptionsResult.emit(filters)

    @qtc.pyqtSlot()
    def get_collections(self):
        """Get collections for a job search. Emits signal with the collections."""
        collections = LinkedInAutomator.get_collections(self)
        self.getCollectionsResult.emit(collections)

    @thread_safe_dbs
    def get_jobs_from_db(self) -> List[Job]:
        """Get all jobs from the database. Emits signal with the jobs. Used to populate the GUI."""
        all_jobs = self.job_app_db.get_models(Job)
        self.getJobsFromDBResult.emit(all_jobs)
        return all_jobs

    @thread_safe_dbs
    def get_questions_from_db(self) -> List[Question]:
        """Get all questions from the database. Emits signal with the questions. Used to populate the GUI."""
        all_questions = self.job_app_db.get_models(Question)
        self.getQuestionsFromDBResult.emit(all_questions)
        return all_questions

    def goto_job(self, job: Job, sleep_secs=0) -> Job:
        """Go to the LinkedIn job page for the given job. Emits signal when the job page has loaded."""
        job = LinkedInAutomator.goto_job(self, job, sleep_secs)
        self.openedJob.emit(job)
        return job

    def update_job(self, job: Job) -> Job:
        """Scrapes the job details for a given job then updates the model and DB. Emits signal with the updated job."""
        job = LinkedInAutomator.update_job(self, job)
        self.updatedJob.emit(job)
        return job

    def iter_jobs(self, filters: dict) -> Iterator[Job]:
        """Iterate over jobs found with the given filters. Emits signal with each job found."""
        for job in LinkedInAutomator.iter_jobs(self, filters):
            self.newJob.emit(job)
            yield job

    @qtc.pyqtSlot(dict)
    @thread_safe_dbs
    def search_jobs(self, filters: dict) -> List[Job]:
        """Search for jobs with the given filters. Emits signal with each job found, and when complete."""
        jobs = list(self.iter_jobs(filters))
        self.searchComplete.emit(jobs)
        return jobs

    @qtc.pyqtSlot(list)
    @thread_safe_dbs
    def scrape_jobs(self, jobs: List[Job]) -> List[Job]:
        """Scrape the details for a list of jobs. Emits signal with each updated job."""
        jobs = list(self.update_jobs(jobs))
        return jobs

    @qtc.pyqtSlot(list)
    @thread_safe_dbs
    def open_jobs(self, jobs: List[Job]) -> List[Job]:
        """Open the LinkedIn job pages in new tab for a list of jobs. Emits signal with each job page opened."""
        jobs = list(LinkedInAutomator.open_jobs(self, jobs))
        return jobs

    @qtc.pyqtSlot(list)
    @thread_safe_dbs
    def apply_to_jobs(self, jobs: List[Job]) -> List[Job]:
        """Apply to a list of jobs. Emits signal with each job applied to, and with the results when complete."""
        sucessful_apply_jobs = []
        for job in LinkedInAutomator.apply_to_jobs(self, jobs):
            self.appliedJob.emit(job)
            sucessful_apply_jobs.append(job)

        self.applyingComplete.emit(len(sucessful_apply_jobs), len(jobs))
        return sucessful_apply_jobs

    def answer_job_question(self, question: Question) -> Question:
        """
        Attempts to get an answer from the AI for a job application question.
        Emits signals when an answer is needed from the user and when the question is updated.
        """
        question = LinkedInAutomator.answer_job_question(self, question)
        if (not question.answer and self.ask_when_answer_needed) or self.verify_ai_answers:
            question = self.get_answer_from_user(question)

        self.updatedQuestion.emit(question)
        return question

    def get_answer_from_user(self, question: Question) -> Question:
        """
        Ask the user for an answer to a job application question.
        Emits signal with the question and waits for the user to provide an answer.
        """

        self.last_question = "AWAITING ANSWER"  # Set last_question to a placeholder value
        self.answerNeeded.emit(
            question
        )  # Emit signal to ask user for answer (which creates a QuestionDialog in the main GUI thread)

        while self.last_question == "AWAITING ANSWER":
            # Process events to allow the GUI to update and wait for an answer or None
            qtc.QCoreApplication.processEvents()

        if self.last_question:
            # Update the question model and DB when an answer is provided by the AI or user
            question = self.last_question
            self.job_app_db.update_model(question)
            print("Answered question:", question.answer)

        return question

    @qtc.pyqtSlot(list)
    @thread_safe_dbs
    def edit_questions(self, questions: List[Question]) -> None:
        """Edit a list of questions. Emits signal with each question edited."""
        for question in questions:
            self.get_answer_from_user(question)
            self.updatedQuestion.emit(question)

    @qtc.pyqtSlot(list)
    @thread_safe_dbs
    def delete_questions(self, questions: List[Question]) -> None:
        """Delete a list of questions. Emits signal with each question deleted."""
        for question in questions:
            self.job_app_db.delete_model(question)
            self.deletedQuestion.emit(question)
            print("Deleted question:", question.question)

    @qtc.pyqtSlot(Question)
    def set_last_question(self, question: Question):
        """Setter slot used to update the last_question attribute from the main GUI thread."""
        self.last_question = question

    @qtc.pyqtSlot(int)
    def set_ask_when_answer_needed(self, ask_when_answer_needed: int):
        """Setter slot used to update the ask_when_answer_needed attribute from the main GUI thread."""
        self.ask_when_answer_needed = ask_when_answer_needed

    @qtc.pyqtSlot(int)
    def set_verify_ai_answers(self, verify_ai_answers: int):
        """Setter slot used to update the verify_ai_answers attribute from the main GUI thread."""
        self.verify_ai_answers = verify_ai_answers


class MainWindow(qtw.QMainWindow):
    def __init__(self, config_path: Path, print_status_updates: bool = True):
        super().__init__()

        self.config_path = config_path
        self.print_status_updates = print_status_updates

        self.setWindowTitle("LinkedIn AI")
        self.setGeometry(100, 100, 800, 800)

        self.central_tab_widget = qtw.QTabWidget()
        self.setCentralWidget(self.central_tab_widget)

        self.search_widget = SearchAndApplyWidget()
        self.job_app_db_view_widget = JobAppDBInteractionWidget()
        self.question_db_view_widget = QuestionDBInteractionWidget()
        self.settings_widget = SettingsWidget(config_path)

        self.central_tab_widget.addTab(self.search_widget, "Search and Apply for Jobs")
        self.central_tab_widget.addTab(self.job_app_db_view_widget, "View Job Database")
        self.central_tab_widget.addTab(self.question_db_view_widget, "View Question Database")
        self.central_tab_widget.addTab(self.settings_widget, "Settings")

        self.login_dialog = LoginDialog(parent=self)
        self.question_dialog = QuestionDialog(parent=self)

        self.li_auto = None
        self.li_thread = None

        # The LinkedInAutomatorQObject will be created and moved to a separate thread when settings are updated
        # All other signals will be connected AFTER the LinkedInAutomatorQObject is created with the updated settings
        self.settings_widget.settingsUpdated.connect(self.setup_li_auto)

        self.show()
        self.is_open = True

        if self.config_path.exists():
            # Set up LinkedInAutomator with the settings from the config file if it exists
            self.setup_li_auto(self.settings_widget.get_settings())
        else:
            # Show a welcome message and get settings if the config file does not exist
            self.central_tab_widget.setCurrentIndex(3)
            qtw.QMessageBox.information(
                self,
                "Welcome to LinkedIn AI",
                "Welcome to LinkedIn AI!\n\n"
                'Configure your settings\nthen click "Update Settings" to get started.\n\n'
                "Required settings include:\n"
                "1. OpenAI API Key\n"
                "2. Webdriver Path",
            )

    def connect_li_automator_signals(self):
        if not self.li_auto:
            raise ValueError("LinkedInAutomator not set up. Call setup_li_auto first.")

        # Login
        self.login_dialog.loginAttempted.connect(self.li_auto.login)
        self.li_auto.loginReady.connect(self.login_dialog.onLoginReady)
        self.li_auto.loginResult.connect(self.login_dialog.onLoginResult)
        self.login_dialog.loginDone.connect(self.populate_ui)

        # Filter options
        self.search_widget.search_filters_widget.getFilterOptions.connect(
            self.li_auto.get_filter_options
        )  # Get filters for search term in LinkedInAutomator thread
        self.search_widget.search_filters_widget.getFilterOptions.connect(
            self.getting_filter_options
        )  # Update statusbar when starting task
        self.li_auto.getFilterOptionsResult.connect(
            self.updated_filter_options
        )  # Update statusbar when done getting filter options
        self.li_auto.getFilterOptionsResult.connect(
            self.search_widget.update_filter_options
        )  # Update filter options in search widget

        # Collections options
        self.search_widget.search_collections_widget.getCollections.connect(
            self.li_auto.get_collections
        )  # Get collections in LinkedInAutomator thread
        self.search_widget.search_collections_widget.getCollections.connect(
            self.getting_collections
        )  # Update statusbar when starting task
        self.li_auto.getCollectionsResult.connect(
            self.updated_collections
        )  # Update statusbar when done getting collections
        self.li_auto.getCollectionsResult.connect(
            self.search_widget.search_collections_widget.update_collections
        )  # Update collections combobox in search widget

        # Search for jobs
        # Begin searching in the LinkedInAutomator thread
        self.search_widget.newSearch.connect(self.li_auto.search_jobs)
        # Update statusbar when starting a new job search
        self.search_widget.newSearch.connect(self.new_search)
        # Add jobs to table as they are found
        self.li_auto.newJob.connect(self.search_widget.jobs_table_widget.append)
        # Update statusbar when new job is found
        self.li_auto.newJob.connect(self.new_job)
        # Update statusbar when search is complete
        self.li_auto.searchComplete.connect(self.search_complete)

        # Apply to jobs
        # Begin applying in the LinkedInAutomator thread
        self.search_widget.applyJobs.connect(self.li_auto.apply_to_jobs)
        # Update statusbar when starting to apply to jobs
        self.search_widget.applyJobs.connect(self.begin_applying)
        # Update statusbar when job is applied to successfully
        self.li_auto.appliedJob.connect(self.applied_job)
        # Update statusbar when applying is complete
        self.li_auto.applyingComplete.connect(self.applying_complete)

        # Answer questions AI could not answer and confirm AI answers when needed
        self.search_widget.ask_when_needed_checkbox.stateChanged.connect(
            self.li_auto.set_ask_when_answer_needed
        )  # Pause to ask user for answer when needed
        self.search_widget.verify_ai_answers_checkbox.stateChanged.connect(
            self.li_auto.set_verify_ai_answers
        )  # Pause to verify all AI provided answers
        # Ask user for answer when needed
        self.li_auto.answerNeeded.connect(self.answer_needed)
        # Update statusbar when question is answered
        self.li_auto.updatedQuestion.connect(self.updated_question)

        # Request jobs from the database
        self.job_app_db_view_widget.getJobsFromDB.connect(self.li_auto.get_jobs_from_db)
        # Populate the jobs table with the jobs from the database
        self.li_auto.getJobsFromDBResult.connect(self.job_app_db_view_widget.update_jobs)
        # Apply to selected jobs in the database
        self.job_app_db_view_widget.applyJobs.connect(self.li_auto.apply_to_jobs)
        self.job_app_db_view_widget.applyJobs.connect(self.begin_applying)
        # Scrape and update selected jobs in the database
        self.job_app_db_view_widget.scrapeJobs.connect(self.li_auto.scrape_jobs)
        self.li_auto.updatedJob.connect(self.updated_job)
        # Open selected jobs in new tabs
        self.job_app_db_view_widget.openJobs.connect(self.li_auto.open_jobs)

        # Request questions from the database
        self.question_db_view_widget.getQuestionsFromDB.connect(self.li_auto.get_questions_from_db)
        # Populate the questions table with the questions from the database
        self.li_auto.getQuestionsFromDBResult.connect(self.question_db_view_widget.update_questions)
        # Edit selected questions in the database
        self.question_db_view_widget.editQuestions.connect(self.li_auto.edit_questions)
        # Delete selected questions in the database
        self.question_db_view_widget.deleteQuestions.connect(self.li_auto.delete_questions)
        self.li_auto.deletedQuestion.connect(self.deleted_question)

        self.li_auto.aiAndDBsInitialized.connect(self.connect_ai_signals)

    @qtc.pyqtSlot()
    def connect_ai_signals(self):
        if not self.li_auto:
            raise ValueError("LinkedInAutomator not set up. Call setup_li_auto first.")
        if not self.li_auto.ai:
            raise ValueError("LinkedIn AI not set up. Call setup_li_auto and init_dbs first.")

        self.li_auto.ai.createdAssistant.connect(self.created_assistant)
        self.li_auto.ai.updatedAssistant.connect(self.updated_assistant)
        self.li_auto.ai.createdThread.connect(self.created_thread)
        self.li_auto.ai.addedMessageToThread.connect(self.added_message_to_thread)
        self.li_auto.ai.createdRun.connect(self.created_run)
        self.li_auto.ai.cancelledRun.connect(self.cancelled_run)
        self.li_auto.ai.runStatusUpdated.connect(self.run_status_updated)
        self.li_auto.ai.runCompleted.connect(self.run_completed)
        self.li_auto.ai.newToolCall.connect(self.new_tool_call)
        self.li_auto.ai.toolOutputsSubmitted.connect(self.tool_outputs_submitted)
        self.li_auto.ai.waitingForResponse.connect(self.waiting_for_response)
        self.li_auto.ai.responseReceived.connect(self.reponse_received)
        self.li_auto.ai.askingQuestion.connect(self.asking_question)
        self.li_auto.ai.answeredQuestion.connect(self.answered_question)
        self.li_auto.ai.answerUnknown.connect(self.answer_unknown)
        self.li_auto.ai.writingCoverLetter.connect(self.writing_cover_letter)
        self.li_auto.ai.wroteCoverLetter.connect(self.wrote_cover_letter)
        self.li_auto.ai.aiError.connect(self.ai_error)

    @qtc.pyqtSlot(dict)
    def setup_li_auto(self, settings):
        self.teardown_li_auto_thread_if_running()

        self.settings = settings
        auto_login = settings.pop("li_auto_login", False)

        self.li_auto = LinkedInAutomatorQObject(
            **settings,
            ask_when_answer_needed=self.search_widget.ask_when_needed_checkbox.isChecked(),
            verify_ai_answers=self.search_widget.verify_ai_answers_checkbox.isChecked(),
        )
        # Create the LinkenInAutomator QObject and move it to a separate thread
        self.li_thread = qtc.QThread()
        self.li_auto.moveToThread(self.li_thread)
        self.li_thread.start()

        self.connect_li_automator_signals()
        self.li_auto.init_scraper()
        self.login(self.settings["li_username"], self.settings["li_password"], auto_login)

    def teardown_li_auto_thread_if_running(self):
        try:
            if self.li_auto:
                self.li_auto.teardown()
        except Exception as e:
            print(e)
        finally:
            if self.li_thread:
                self.li_thread.quit()

    def login(self, li_username: Optional[str], li_password: Optional[str], auto_login=False):
        if not self.li_auto:
            raise ValueError("LinkedInAutomator not set up. Call setup_li_auto first.")

        self.li_auto.goto_login()
        self.login_dialog.set_texts(li_username, li_password)
        if auto_login and li_username and li_password:
            self.login_dialog.auto_login(li_username, li_password)
        else:
            # Show login dialog and start or exit accordingly
            if self.login_dialog.exec_() == qtw.QDialog.Accepted:
                print("Login successful")
            else:
                print("Login canceled")
                self.close()

    @qtc.pyqtSlot()
    def populate_ui(self):
        if not self.li_auto:
            raise ValueError("LinkedInAutomator not set up. Call setup_li_auto first.")

        self.central_tab_widget.setCurrentIndex(0)
        sleep(1)
        self.li_auto.get_jobs_from_db()
        self.li_auto.get_questions_from_db()
        self.li_auto.get_filter_options("Python Automation")
        self.li_auto.get_collections()

    @qtc.pyqtSlot(str)
    def update_status(self, status_message: str):
        self.statusBar().showMessage(status_message)
        if self.print_status_updates:
            print(status_message)

    # LinkedInAutomator Slots
    @qtc.pyqtSlot(str)
    def getting_filter_options(self, search_term: str):
        self.update_status(f"Getting Filter Options for {search_term}...")

    @qtc.pyqtSlot(dict)
    def updated_filter_options(self, filters):
        self.update_status(f'Updated Filter Options: {" | ".join(filters)}')

    @qtc.pyqtSlot()
    def getting_collections(self):
        self.update_status("Getting Collections...")

    @qtc.pyqtSlot(dict)
    def updated_collections(self, collections):
        self.update_status(f'Updated Collections: {" | ".join(collections)}')

    @qtc.pyqtSlot(dict)
    def new_search(self, filters):
        self.update_status(
            f"Searching for {filters.get('search_term') or filters.get('collection')} jobs in {filters.get('location') or 'your LinkedIn recommendations'}"
        )

    @qtc.pyqtSlot(Job)
    def new_job(self, job):
        self.update_status(f"Found Job ({job.id}): {job.title} at {job.company.name}")

    @qtc.pyqtSlot(Job)
    def opened_job(self, job):
        self.update_status(f"Opened Job ({job.id}): {job.title} at {job.company.name}")

    @qtc.pyqtSlot(Job)
    def updated_job(self, job):
        self.update_status(f"Updated Job ({job.id}): {job.title} at {job.company.name}. Status: {job.status}")

    @qtc.pyqtSlot(list)
    def search_complete(self, jobs):
        self.update_status(f"Search complete. Found {len(jobs)} jobs.")

    @qtc.pyqtSlot(list)
    def begin_applying(self, jobs):
        self.update_status(f"Applying to {len(jobs)} jobs...")

    @qtc.pyqtSlot(Job)
    def applied_job(self, job):
        self.update_status(f"Applied to Job ({job.id}): {job.title} at {job.company.name}")
        self.search_widget.jobs_table_widget.remove_item(job)

    @qtc.pyqtSlot(int, int)
    def applying_complete(self, sucessful_jobs, total_jobs):
        self.update_status(
            f"Applied to {sucessful_jobs} jobs. {total_jobs - sucessful_jobs} jobs need input or failed."
        )

    @qtc.pyqtSlot(Question)
    def answer_needed(self, question):
        self.update_status(f"Answer needed for question: {question.question}")
        self.question_dialog.ask_question(question)

        question = self.question_dialog.get_answered_question()
        self.li_auto.set_last_question(question)

    @qtc.pyqtSlot(Question)
    def updated_question(self, question):
        self.update_status(f"Answered question: {question.question}. Answer: {question.answer}")

    @qtc.pyqtSlot(Question)
    def deleted_question(self, question):
        self.update_status(f"Deleted question: {question.question}")

    # JobAppAI Slots
    @qtc.pyqtSlot(Assistant)
    def created_assistant(self, assistant):
        self.update_status(f"Created assistant: {assistant.id}")

    @qtc.pyqtSlot(Assistant, dict)
    def updated_assistant(self, assistant, data):
        self.update_status(f"Updated assistant: {assistant.id} with {data}")

    @qtc.pyqtSlot(Thread)
    def created_thread(self, thread):
        self.update_status(f"Created thread: {thread.id}")

    @qtc.pyqtSlot(Message)
    def added_message_to_thread(self, message):
        self.update_status(
            f"Added message: {message.id} to thread: {message.thread_id} with content: {message.content}"
        )

    @qtc.pyqtSlot(Run)
    def created_run(self, run):
        self.update_status(f"Created run: {run.id}")

    @qtc.pyqtSlot(Run)
    def cancelled_run(self, run):
        self.update_status(f"Cancelled run: {run.id}")

    @qtc.pyqtSlot(Run)
    def run_status_updated(self, run):
        self.update_status(f"Run {run.id} status updated: {run.status}")

    @qtc.pyqtSlot(Run)
    def run_completed(self, run):
        self.update_status(f"Run {run.id} completed successfully with status: {run.status}")

    @qtc.pyqtSlot(str, dict)
    def new_tool_call(self, tool_name, arguments):
        self.update_status(f"AI called tool: {tool_name} with arguments: {arguments}")

    @qtc.pyqtSlot(str, dict, object)
    def tool_outputs_submitted(self, tool_name, arguments, outputs):
        self.update_status(f"Submitted tool {tool_name} outputs to AI: {outputs} for arguments: {arguments}")

    @qtc.pyqtSlot(int)
    def waiting_for_response(self, sleep_interval):
        self.update_status(f"Waiting {sleep_interval} seconds for response from AI")

    @qtc.pyqtSlot(object)
    def reponse_received(self, messages):
        if messages.data:
            self.update_status(f"Received response from AI: {messages.data[0]}")

    @qtc.pyqtSlot(Question)
    def asking_question(self, question):
        self.update_status(f"Asking AI question: {question.question}")

    @qtc.pyqtSlot(Question)
    def answered_question(self, question):
        self.update_status(f"Answered AI question: {question.question} with answer: {question.answer}")

    @qtc.pyqtSlot(Question)
    def answer_unknown(self, question):
        self.update_status(f"AI could not answer question: {question.question}")

    @qtc.pyqtSlot(Job)
    def writing_cover_letter(self, job):
        self.update_status(f"Writing cover letter for job: {job.title} at {job.company.name}")

    @qtc.pyqtSlot(Job, str)
    def wrote_cover_letter(self, job, cover_letter_text):
        self.update_status(f"Wrote cover letter for job: {job.title} at {job.company.name}: {cover_letter_text}")

    # Error handling Slots
    def handle_error(
        self,
        critical: bool = True,
        error_code: str = "Unknown Error",
        error_message: str = "An unknown error occurred.",
        prefix="ERROR ",
        item_sep=", ",
        kv_sep=": ",
        section_sep="\n\n",
        help_message="",
        button_message="Press OK to quit.",
        buttons=qtw.QMessageBox.Ok,
        **kwargs,
    ):
        """
        Generic error handling method that shows an error message box and updates the status bar.
        If the error is critical it will immediately tear down the LinkedInAutomator thread,
        before showing the error message, then trigger a closeEvent to gracefully close the app after.
        """

        error_title = f"{prefix}{error_code}"
        error_dict = {error_title: error_message, **kwargs}

        status_message = item_sep.join(f"{k}{kv_sep}{v}" for k, v in error_dict.items())
        self.update_status(status_message)

        sections = filter(bool, (error_title, error_message, help_message, button_message))
        error_message_box_text = section_sep.join(sections)

        if critical:
            # If the error is critical, tear down the LinkedInAutomator thread before showing the error message
            self.teardown_li_auto_thread_if_running()
            message_box_cls = qtw.QMessageBox.critical
        else:
            message_box_cls = qtw.QMessageBox.warning

        # Show the error message box
        message_box_cls(self, error_title, error_message_box_text, buttons)
        # Close the app if the error is critical
        if critical:
            self.close()

    @qtc.pyqtSlot(AIError)
    def ai_error(self, error: AIError):
        self.handle_error(
            critical=error.is_critical,
            error_code=error.stdcode,
            error_message=error.stdmessage,
            prefix=f"{error.clsname} ",
        )

    def closeEvent(self, event):
        print("Quitting...")
        self.teardown_li_auto_thread_if_running()
        print("Teardown complete.")
        event.accept()
        print("closeEvent accepted.")
        self.is_open = False
        app.quit()
        print("LinkedIn AI exited successfully.")
        exit(0)


# Global QApplication instance so it can be quit when a closeEvent occurs
app = qtw.QApplication([])


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--config-path",
        "-c",
        type=Path,
        default=Path("./linkedin-ai-config.json"),
    )
    args = parser.parse_args()

    try:
        window = MainWindow(config_path=args.config_path)
        app.exec()
    except KeyboardInterrupt:
        if window.is_open:
            window.close()


if __name__ == "__main__":
    main()
