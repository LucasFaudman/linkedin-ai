from typing import Optional, List, Dict, Tuple, Iterable, Type
from pathlib import Path
from functools import wraps
from datetime import datetime
from docx import Document
from PyQt5 import QtCore as qtc
from .core.aimanager import (
    OpenAIManager,
    Assistant,
    Thread,
    Run,
    Message,
    OpenAIError,
    RunStatusError,
    sleep,
    json_loads,
)
from .jobdb import JobAppDB
from .models import Question, Job


class AIError:
    def __init__(
        self,
        error: Exception,
        critical_errors: Tuple[Type[Exception], ...] = (RunStatusError,),
        stdcode_parts: Iterable[str] = ("status", "status_code", "code", "type"),
        stdmessage_parts: Iterable[str] = ("message", "detail", "description"),
    ) -> None:
        self._error = error
        self.is_critical = self.check_critical(critical_errors)
        self.stdcode = " ".join(self.iter_stdcode_parts(stdcode_parts)) or "UnknownAIError"
        self.stdmessage = f"{self.stdcode}: " + (
            " ".join(self.iter_stdmessage_parts(stdmessage_parts)) or "Unknown AI Error"
        )
        self.clsname = type(error).__name__

        print(f"AI Error: {self.stdmessage}")

    def check_critical(self, critical_errors: Tuple[Type[Exception], ...]) -> bool:
        """
        Determines if an OpenAI error is critical and should be raised.
        """
        return isinstance(self._error, critical_errors)

    def iter_stdcode_parts(self, stdcode_parts: Iterable[str]) -> Iterable[str]:
        """
        Standardizes the error code for an OpenAI error.
        """
        for attr in stdcode_parts:
            if (val := getattr(self._error, attr, None)) is not None:
                yield (val if isinstance(val, str) else str(val)).replace("_", " ").title()

    def iter_stdmessage_parts(self, stdmessage_parts: Iterable[str]) -> Iterable[str]:
        """
        Standardizes the error message for an OpenAI error.
        """
        for attr in stdmessage_parts:
            if (val := getattr(self._error, attr, None)) is not None:
                yield val if isinstance(val, str) else str(val)

    def __str__(self) -> str:
        return self.stdmessage


def emit_ai_errors(func):
    """
    Decorator to ensure that OpenAI errors are caught and emitted as signals.
    """

    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        try:
            return func(instance, *args, **kwargs)
        except (OpenAIError, RunStatusError) as e:
            aierror = AIError(e)
            print(f"Caught AI Error: {e}. \nEmitting as AIError signal: {aierror}")
            instance.aiError.emit(aierror)
            raise e

    return wrapper


class OpenAIManagerQObject(OpenAIManager, qtc.QObject):
    """OpenAIManager with PyQt signals for emitting events."""

    # Signals
    createdAssistant = qtc.pyqtSignal(Assistant)
    updatedAssistant = qtc.pyqtSignal(Assistant, dict)
    createdThread = qtc.pyqtSignal(Thread)
    addedMessageToThread = qtc.pyqtSignal(Message)
    createdRun = qtc.pyqtSignal(Run)
    cancelledRun = qtc.pyqtSignal(Run)
    runStatusUpdated = qtc.pyqtSignal(Run)
    runCompleted = qtc.pyqtSignal(Run)
    newToolCall = qtc.pyqtSignal(str, dict)
    toolOutputsSubmitted = qtc.pyqtSignal(str, dict, object)
    waitingForResponse = qtc.pyqtSignal(int)
    responseReceived = qtc.pyqtSignal(object)
    aiError = qtc.pyqtSignal(AIError)

    def __init__(self, *args, **kwargs) -> None:
        qtc.QObject.__init__(self)
        OpenAIManager.__init__(self, *args, **kwargs)

    def create_assistant(self, *args, **kwargs) -> Assistant:
        """Creates an assistant and emits createdAssistant signal with the Assistant object."""
        assistant = OpenAIManager.create_assistant(self, *args, **kwargs)
        self.createdAssistant.emit(assistant)
        return assistant

    def create_thread(self, *args, **kwargs) -> Thread:
        """Creates a thread and emits createdThread signal with the Thread object."""
        thread = OpenAIManager.create_thread(self, *args, **kwargs)
        self.createdThread.emit(thread)
        return thread

    def create_run(self, *args, **kwargs) -> Run:
        """Creates a run and emits createdRun signal with the Run object."""
        run = OpenAIManager.create_run(self, *args, **kwargs)
        self.createdRun.emit(run)
        return run

    def cancel_run(self, *args, **kwargs) -> Run:
        """Cancels a run and emits cancelledRun signal with the Run object."""
        cancelled_run = OpenAIManager.cancel_run(self, *args, **kwargs)
        self.cancelledRun.emit(cancelled_run)
        return cancelled_run

    def add_message_to_thread(self, *args, **kwargs) -> Message:
        """Adds a message to a thread and emits addedMessageToThread signal with the Message object."""
        message = OpenAIManager.add_message_to_thread(self, *args, **kwargs)
        self.addedMessageToThread.emit(message)
        return message

    def wait_for_response(self, thread_id, run_id, sleep_interval=1, **kwargs):
        """
        Waits for a response and handles status updates.
        Calls handle_submit_tool_outputs_required to submit tool outputs when run requires action.
        Returns messages once recursive loop is complete.

        Emits signals:
        - runStatusUpdated: when run status is updated emit the run object
        - runCompleted: when run status is completed emit the run object
        - waitingForResponse: when waiting for response emit the sleep interval
        - responseReceived: when messages are received emit the messages object
        """
        run = None
        while not run or run.status in ("queued", "in_progress"):
            run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

            if self.db:
                self.db.update_model(run)

            print(f"Status: {run.status} Thread id: {thread_id}, run_id: {run_id}")
            self.runStatusUpdated.emit(run)

            if run.status == "requires_action":
                # Handles tool calls and submits tool outputs to run then recursively calls wait_for_response
                return self.handle_submit_tool_outputs_required(run, sleep_interval, **kwargs)

            if run.status in ("cancelled", "failed", "expired", "error") and run.last_error:
                raise RunStatusError(run.status, run.last_error)

            if run.status == "completed":
                print(f"Run {run.id} completed")
                self.runCompleted.emit(run)
                break

            print(f"Waiting {sleep_interval} seconds for response")
            self.waitingForResponse.emit(sleep_interval)
            sleep(sleep_interval)

        messages = self.client.beta.threads.messages.list(thread_id)
        if self.db:
            self.db.update_models(*messages)

        self.responseReceived.emit(messages)
        return messages

    def handle_submit_tool_outputs_required(self, run, sleep_interval=1, **kwargs):
        """
        Executes tool calls and submits tool outputs to run.

        Emits signals:
        - newToolCall: when a new tool call is made emit the tool name and arguments
        - toolOutputsSubmitted: when tool outputs are submitted emit the tool name, arguments, and tool output
        """

        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            tool_name = tool_call.function.name
            arguments = json_loads(tool_call.function.arguments)

            print(f"\nAI called tool: {tool_name}\nwith args: {arguments}")
            self.newToolCall.emit(tool_name, arguments)

            # Get tool output with _do_tool_call
            tool_output = self._do_tool_call(tool_name, arguments, **kwargs)
            print(f"\nSubmitting tool output: {tool_output}")
            self.toolOutputsSubmitted.emit(tool_name, arguments, tool_output)

            # Format tool output and add to tool_outputs list
            tool_outputs.append(
                {
                    "tool_call_id": tool_call.id,
                    "output": self.format_content(tool_output),
                }
            )

        # Submit tool outputs to run and get updated run
        run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=run.thread_id, run_id=run.id, tool_outputs=tool_outputs
        )

        # Recursively call wait_for_response to handle next required_action
        return self.wait_for_response(run.thread_id, run.id, sleep_interval, **kwargs)


class JobAppAI(OpenAIManagerQObject):
    """OpenAIManager for answering job application questions, generating cover letters, and more to be added."""

    askingQuestion = qtc.pyqtSignal(Question)
    answeredQuestion = qtc.pyqtSignal(Question)
    answerUnknown = qtc.pyqtSignal(Question)
    writingCoverLetter = qtc.pyqtSignal(Job)
    wroteCoverLetter = qtc.pyqtSignal(Job, str)

    # AI Tool/Function definition for searching job application database for questions
    SEARCH_JOB_DB_FOR_QUESTIONS_TOOL = {
        "type": "function",
        "function": {
            "name": "search_answered_questions_db",
            "description": "Search the database of previously answered questions for question:answer pairs matching the provided keywords.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords to search for in the database of previously answered questions. The search is case sensitive.",
                    },
                },
                "required": ["keywords"],
            },
        },
    }

    def __init__(
        self,
        job_app_db: JobAppDB,
        ai_db_path: Optional[Path] = Path("ai.db"),
        assistant_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        api_key: str = "OPENAI_API_KEY",
        model: str = "gpt-4-turbo-preview",
        resume: str = "",
        cover_letter_output_dir: Path = Path("./cover-letters/"),
        cover_letter_start_text: str = "Dear Hiring Manager,",
        cover_letter_end_text: str = "Sincerely,\n<Candidate Name>",
        cover_letter_example_texts: Optional[List[str]] = None,
    ) -> None:
        self.job_app_db = job_app_db
        self.assistant_id = assistant_id
        self.thread_id = thread_id
        self.run_id = None
        tools = {
            "search_answered_questions_db": (
                self.SEARCH_JOB_DB_FOR_QUESTIONS_TOOL,
                self.search_answered_questions_db,
            )
        }

        self.resume = resume
        self.cover_letter_output_dir = cover_letter_output_dir
        self.cover_letter_start_text = cover_letter_start_text
        self.cover_letter_end_text = cover_letter_end_text
        self.cover_letter_example_texts = cover_letter_example_texts

        super().__init__(api_key=api_key, model=model, tools=tools, db_path=ai_db_path)

    def search_answered_questions_db(self, arguments: dict) -> Dict[str, str]:
        """Search the database of previously answered questions for question:answer pairs matching the provided keywords."""
        keywords = arguments["keywords"]
        questions = self.job_app_db.get_questions_containing_keywords(*keywords)
        tool_output = {question.question: question.answer for question in questions if question.answer}
        return tool_output

    def add_resume_to_system_prompt(self, system_prompt: str) -> str:
        """Add resume to system prompt."""
        return system_prompt + f"\nResume:\n{self.resume}"

    @emit_ai_errors
    def answer_job_questions(self, *questions: Question) -> Tuple[Question, ...]:
        """
        Answers job application questions using the AI assistant.
        Updates the question object with the answer when the answer is not 'ANSWER UNKNOWN'.
        Returns a tuple of updated question objects.

        Emits signals:
        - askingQuestion: when beginning asking a question emit the question object
        - answeredQuestion: when a question is answered emit the question object
        - answerUnknown: when a question is answered with 'ANSWER UNKNOWN' emit the question object
        """

        system_prompt = "".join(
            (
                "Your role is to answer job application questions as if you were the candidate. ",
                "\nUse the 'search_answered_questions_db' function to search for previously answered questions in the database. ",
                "\nIMPORTANT: If you can't determine the answer after querying the database, respond with 'ANSWER UNKNOWN'. ",
                "\nIMPORTANT: Some questions will have a list of choices. When choices are provided, your response MUST be one of strings in the list of choices. ",
                "\nIMPORTANT: When asked a question that can be answered with a number, your response MUST be a whole number between 0 and 99, WITHOUT ANY text before or after the number. ",
                "For example, if the question is 'How many years of experience do you have with Python?', and the answer is 6 years, respond with '6'.",
                f"\nThe current date is: {datetime.now().strftime('%Y-%m-%d')}.\n",
            )
        )

        system_prompt = self.add_resume_to_system_prompt(system_prompt)

        for question in questions:
            print(f"\n\nAsking: {question.question}")
            self.askingQuestion.emit(question)

            ass, thread, run, messages = self.run_with_assistant(
                str(
                    question
                ),  # Leverage pydantic BaseModel builtin __str__ method to format questions with/without choices accordingly
                ass_id=self.assistant_id,
                thread_id=self.thread_id,
                system_prompt=system_prompt,
                tool_names=["search_answered_questions_db"],
                sleep_interval=1,
            )

            self.assistant_id = ass.id
            self.thread_id = thread.id
            self.run_id = run.id

            answer = messages.data[0].content[0].text.value
            if "ANSWER UNKNOWN" not in answer.upper():
                question.answer = answer
                self.answeredQuestion.emit(question)
            else:
                self.answerUnknown.emit(question)

            print(f"\nDone with: {question.question}\nAnswer: {answer}")

        return questions

    @emit_ai_errors
    def write_job_cover_letters(self, *jobs: Job) -> Dict[Job, Path]:
        """
        Writes job application cover letters using the AI assistant.
        Creates a .docx in cover_letter_output_dir named: {job.company.name}-{job.id}-cover-letter.docx
        Returns a dict of Job:Path pairs

        Emits signals:
        - writingCoverLetter: when beginning writing a cover letter for a job, emit the job
        - wroteCoverLetter: when done writing a cover letter for a job, emits the job and cover letter text
        """

        system_prompt = "".join(
            (
                "Your role is to write cover letters for application as if you were the candidate. ",
                "You will be provided with a job description and must write a cover letter for the job "
                "using the information from the candidate's resume and the job description. ",
                "The cover letter must be tailored to the job description and the candidate's resume. ",
                "The cover letter should be professional and well-written. ",
                "The cover letter should highlight the candidate's skills and experiences that are relevant to the job. ",
                f"IMPORTANT: The cover letter MUST BEGIN WITH: '{self.cover_letter_start_text}'. "
                f"IMPORTANT: The cover letter MUST END WITH: '{self.cover_letter_end_text}'. ",
            )
        )

        system_prompt = self.add_resume_to_system_prompt(system_prompt)

        if self.cover_letter_example_texts:
            for i, example_cover_letter in enumerate(self.cover_letter_example_texts, start=1):
                system_prompt += f"\n\nExample Cover Letter {i}:\n{example_cover_letter}"

        cover_letter_paths = {}
        for job in jobs:
            print(f"\n\nWriting cover letter for Job ({job.id}): {job.title} at {job.company.name}")
            self.writingCoverLetter.emit(job)

            ass, thread, run, messages = self.run_with_assistant(
                f"Job Description for {job.title} at {job.company.name}:\n{job.description}",
                ass_id=self.assistant_id,
                thread_id=self.thread_id,
                system_prompt=system_prompt,
                tool_names=["search_answered_questions_db"],
                sleep_interval=1,
            )

            self.assistant_id = ass.id
            self.thread_id = thread.id
            self.run_id = run.id

            cover_letter_text = messages.data[0].content[0].text.value
            cover_letter_path = self.cover_letter_output_dir / f"{job.company.name}-{job.id}-cover-letter.docx"
            cover_letter_doc = Document()
            cover_letter_doc.add_paragraph(cover_letter_text)
            cover_letter_doc.save(str(cover_letter_path))
            cover_letter_paths[job] = cover_letter_path

            print(f"\nDone writing cover letter for Job ({job.id}): {job.title} at {job.company.name}")
            self.wroteCoverLetter.emit(job, cover_letter_text)

        return cover_letter_paths
