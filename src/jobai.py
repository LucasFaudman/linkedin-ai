from typing import Union, Optional, Dict, Tuple, Callable
from pathlib import Path
from datetime import datetime

from PyQt5 import QtCore as qtc
from core.aimanager import OpenAIManager, Assistant, Thread, Run, Message, RunStatusError, sleep, json_loads
from jobdb import JobAppDB
from models import Question


class OpenAIManagerQObject(OpenAIManager, qtc.QObject):
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

    def __init__(self, *args, **kwargs) -> None:
        qtc.QObject.__init__(self)
        OpenAIManager.__init__(self, *args, **kwargs)

    def create_assistant(self, *args, **kwargs) -> Assistant:
        assistant = OpenAIManager.create_assistant(self, *args, **kwargs)
        self.createdAssistant.emit(assistant)
        return assistant
    
    def create_thread(self, *args, **kwargs) -> Thread:
        thread = OpenAIManager.create_thread(self, *args, **kwargs)
        self.createdThread.emit(thread)
        return thread
    
    def create_run(self, *args, **kwargs) -> Run:
        run = OpenAIManager.create_run(self, *args, **kwargs)
        self.createdRun.emit(run)
        return run
    
    def add_message_to_thread(self, *args, **kwargs) -> Message:
        message = OpenAIManager.add_message_to_thread(self, *args, **kwargs)
        self.addedMessageToThread.emit(message)
        return message
    
    def cancel_run(self, *args, **kwargs):
        cancelled_run = OpenAIManager.cancel_run(self, *args, **kwargs)
        self.cancelledRun.emit(cancelled_run)
        return cancelled_run

    def wait_for_response(self, thread_id, run_id, sleep_interval=5, **kwargs):
        """
        Waits for a response and handles status updates. 
        Calls handle_submit_tool_outputs_required to submit tool outputs when run requires action.
        Returns messages once recursive loop is complete. 
        """
        run = None
        while not run or run.status in ("queued", "in_progress"):
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )

            if self.db:
                self.db.update_model(run)            

            print(f"Status: {run.status} Thread id: {thread_id}, run_id: {run_id}")
            self.runStatusUpdated.emit(run)
            
            if run.status == "requires_action":
                # Handles tool calls and submits tool outputs to run then recursively calls wait_for_response
                return self.handle_submit_tool_outputs_required(run, sleep_interval, **kwargs)

            elif run.status in ("cancelled", 'failed', 'expired'):
                raise RunStatusError(run.status, run.last_error)

            elif run.status == "completed":
                print(f"Run {run.id} completed")
                self.runCompleted.emit(run)
                break

            else:
                print(f"Waiting {sleep_interval} seconds for response")
                self.waitingForResponse.emit(sleep_interval)
                sleep(sleep_interval)

        
        messages = self.client.beta.threads.messages.list(thread_id)
        if self.db:
            self.db.update_models(*messages)
        
        self.responseReceived.emit(messages)
        return messages

    
    def handle_submit_tool_outputs_required(self, run, sleep_interval=5, **kwargs):
        """Executes tool calls and submits tool outputs to run."""

        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            tool_name = tool_call.function.name
            arguments = json_loads(tool_call.function.arguments)

            print(f'\nAI called tool: {tool_name}\nwith args: {arguments}')
            self.newToolCall.emit(tool_name, arguments)
            
            # Get tool output with _do_tool_call
            tool_output = self._do_tool_call(tool_name, arguments, **kwargs)
            print(f'\nSubmitting tool output: {tool_output}')
            self.toolOutputsSubmitted.emit(tool_name, arguments, tool_output)

            # Format tool output and add to tool_outputs list
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output":  self.format_content(tool_output)
            })

        # Submit tool outputs to run and get updated run
        run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=run.thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )

        # Recursively call wait_for_response to handle next required_action
        return self.wait_for_response(run.thread_id, run.id, sleep_interval, **kwargs)


class JobAppAI(OpenAIManagerQObject):
    askingQuestion = qtc.pyqtSignal(Question)
    answeredQuestion = qtc.pyqtSignal(Question)
    answerUnknown = qtc.pyqtSignal(Question)

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
                                "description":
                                "Keywords to search for in the database of previously answered questions. The search is case sensitive."
                            },
                        },
                        "required": ["keywords"]
                    }
                }
    }

    def __init__(self,
                 resume: str,
                 job_app_db: JobAppDB,
                 ai_db_path: Optional[Path] = Path("ai.db"),
                 assistant_id: Optional[str] = None,
                 thread_id: Optional[str] = None,
                 api_key: str = "OPENAI_API_KEY",
                 model: str = "gpt-4-turbo-preview"
                 ) -> None:

        self.resume = resume
        self.job_app_db = job_app_db
        self.assistant_id = assistant_id
        self.thread_id = thread_id
        tools = {"search_answered_questions_db": (
            self.SEARCH_JOB_DB_FOR_QUESTIONS_TOOL, self.search_answered_questions_db)}
        super().__init__(api_key=api_key, model=model, tools=tools, db_path=ai_db_path)

    def search_answered_questions_db(self, arguments: dict) -> dict[str, str]:
        """Search the database of previously answered questions for question:answer pairs matching the provided keywords."""
        keywords = arguments["keywords"]
        questions = self.job_app_db.get_questions_containing_keywords(*keywords)
        tool_output = {
            question.question: question.answer for question in questions if question.answer}
        return tool_output

    def answer_job_questions(self, *questions: Question) -> tuple:
        system_prompt = ''.join((
            "Your role is to answer job application questions as if you were the candidate. ",
            "\nUse the 'search_answered_questions_db' function to search for previously answered questions in the database. ",
            "\nIMPORTANT: If you can't determine the answer after querying the database, respond with 'ANSWER UNKNOWN'. ",
            "\nIMPORTANT: Some questions will have a list of choices. When choices are provided, your response MUST be one of strings in the list of choices. ",
            "\nIMPORTANT: When asked a question that can be answered with a number, your response MUST be a whole number between 0 and 99, WITHOUT ANY text before or after the number. ",
            "For example, if the question is 'How many years of experience do you have with Python?', and the answer is 6 years, respond with '6'.",
            f"\nThe current date is: {datetime.now().strftime('%Y-%m-%d')}.\n",
            "\nResume:\n",
            self.resume,
        ))

        for question in questions:
            print(f"\n\nAsking: {question.question}")
            self.askingQuestion.emit(question)

            ass, thread, run, messages = self.run_with_assistant(
                str(question),
                ass_id=self.assistant_id,
                thread_id=self.thread_id,
                system_prompt=system_prompt,
                tools_names=["search_answered_questions_db"],
                sleep_interval=1
            )

            self.assistant_id = ass.id
            self.thread_id = thread.id
            self.run_id = run.id

            run_steps = self.client.beta.threads.runs.steps.list(
                run_id=self.run_id,
                thread_id=self.thread_id,
                limit=100,
                order="asc"
            )
            if self.db:
                self.db.insert_models(*run_steps)

            answer = messages.data[0].content[0].text.value
            if "ANSWER UNKNOWN" not in answer.upper():
                question.answer = answer
                self.job_app_db.update_model(question)
                self.answerUnknown.emit(question)

            print(f"\n Done with: {question.question}\nAnswer: {answer}")
            self.answeredQuestion.emit(question)

        return questions
