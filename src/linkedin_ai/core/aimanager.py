from ast import literal_eval as ast_literal_eval
from pathlib import Path
from json import loads as json_loads, dumps as json_dumps
from time import sleep
from typing import Optional, Dict, Tuple, Callable

from openai import OpenAI, OpenAIError, BadRequestError
from openai.types.beta import Assistant, Thread
from openai.types.beta.threads import Message, Run, Text
from openai.types.beta.threads.run import LastError
from openai.types.beta.threads.runs import RunStep
from openai.types.beta.threads.runs.message_creation_step_details import (
    MessageCreationStepDetails,
)
from openai.types.beta.threads.runs.tool_calls_step_details import ToolCallsStepDetails
from openai.types.beta.threads.file_citation_annotation import FileCitationAnnotation
from openai.types.beta.threads.text_content_block import TextContentBlock
from openai.types.beta.threads.image_file_content_block import ImageFileContentBlock
from openai.types.beta.threads.file_path_annotation import FilePathAnnotation
from openai.types.beta.threads.runs.function_tool_call import FunctionToolCall, Function
from openai.types.beta.threads.runs.code_interpreter_tool_call import (
    CodeInterpreterToolCall,
)
from openai.types.beta.code_interpreter_tool import CodeInterpreterTool
from openai.types.beta.function_tool import FunctionTool

from tiktoken import get_encoding, encoding_for_model

from .sqldantic import BaseDB, pluralize


class OpenAIDB(BaseDB):
    BASE_MODELS = [
        Message,
        Text,
        TextContentBlock,
        ImageFileContentBlock,
        CodeInterpreterTool,
        CodeInterpreterToolCall,
        Function,
        FunctionTool,
        FunctionToolCall,
        FileCitationAnnotation,
        FilePathAnnotation,
        LastError,
        Assistant,
        Thread,
        Run,
        RunStep,
        MessageCreationStepDetails,
        ToolCallsStepDetails,
    ]

    def __init__(self, db_path, **kwargs) -> None:
        super().__init__(
            db_path,
            *self.BASE_MODELS,
            ignore_sqlite_errors=True,
            table_name_transformer=pluralize,
            **kwargs,
        )


class RunStatusError(Exception):
    """Run status is cancelled, failed, or expired"""

    def __init__(self, status, last_error) -> None:
        self.status = status
        self.code = last_error.code
        self.message = last_error.message
        super().__init__(f"Run status: {status}, code: {self.code}, message: {self.message}")


class RateLimitError(Exception):
    """OpenAI API rate limit reached"""


class OpenAIManager:
    def __init__(
        self,
        api_key="OPENAI_API_KEY",
        model="gpt-3.5-turbo",
        tools: Optional[Dict[str, Tuple[Dict, Callable]]] = None,
        openai_kwargs: Optional[Dict] = None,
        db_path: Optional[Path] = Path("ai.db"),
        db_kwargs: Optional[Dict] = None,
    ) -> None:
        openai_kwargs = openai_kwargs if openai_kwargs is not None else {}
        self.client = OpenAI(api_key=api_key, **openai_kwargs)
        self.model = model
        self.tools = tools if tools is not None else {}
        # To store Assistants, Threads, Runs, and Message Objects by id
        self.ai_assistants = {}
        self.ai_threads = {}
        self.ai_messages = {}
        self.ai_runs = {}

        if db_path:
            db_kwargs = db_kwargs if db_kwargs is not None else {}
            self.db = OpenAIDB(db_path, **db_kwargs)
        else:
            self.db = None

    def set_model(self, model):
        self.model = model
        print(f"Changed OpenAI model to {self.model}")

    def num_tokens_from_messages(self, messages, disallowed_special=()):
        """Returns the number of tokens used by a list of messages."""
        try:
            encoding = encoding_for_model(self.model)
        except KeyError:
            encoding = get_encoding("cl100k_base")
        if self.model:
            num_tokens = 0
            for message in messages:
                # every message follows <im_start>{role/name}\n{content}<im_end>\n
                num_tokens += 4
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value, disallowed_special=disallowed_special))
                    if key == "name":  # if there's a name, the role is omitted
                        num_tokens += -1  # role is always required and always 1 token

            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens, (num_tokens / 1000) * 0.01
        else:
            raise NotImplementedError(
                f"""num_tokens_from_messages() is not presently implemented for model {self.model}.
    See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
            )

    def recursively_make_serializeable(self, obj):
        """Recursively makes an object serializeable by converting it to a dict or list of dicts and converting all non-string values to strings."""
        serializeable_types = (str, int, float, bool, type(None))
        if isinstance(obj, serializeable_types):
            return obj
        if isinstance(obj, dict):
            return {k: self.recursively_make_serializeable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.recursively_make_serializeable(item) for item in obj]
        return str(obj)

    def format_content(self, content):
        """Formats content for use a message content. If content is not a string, it is converted to json_"""
        if not isinstance(content, str):
            content = self.recursively_make_serializeable(content)
            content = json_dumps(content, indent=0)

        return content

    def index_content(self, content):
        """Indexes items in sequence into dict with indices as keys."""
        return dict(enumerate(content))

    def create_assistant(self, **kwargs):
        """Creates an Assistant and store it in the OpenAIDB if database is enabled (db_path is set)."""

        assistant = self.client.beta.assistants.create(
            model=kwargs.pop("model", self.model),
            **kwargs,
        )

        if self.db:
            self.db.insert_model(assistant)

        self.ai_assistants[assistant.id] = assistant
        return assistant

    def create_thread(self):
        """Creates a Thread and store it in the OpenAIDB if database is enabled (db_path is set)."""

        thread = self.client.beta.threads.create()

        if self.db:
            self.db.insert_model(thread)

        self.ai_threads[thread.id] = thread
        return thread

    def create_run(self, ass_id, thread_id, **kwargs):
        """Creates a Run and store it in the OpenAIDB if database is enabled (db_path is set)."""
        run = self.client.beta.threads.runs.create(assistant_id=ass_id, thread_id=thread_id, **kwargs)

        if self.db:
            self.db.insert_model(run)

        self.ai_runs[run.id] = run
        return run

    def get_assistant(self, ass_id):
        """Gets Assistant from self or openai client if not retrieved yet"""
        assistant = self.ai_assistants.get(ass_id)

        if not assistant:
            assistant = self.client.beta.assistants.retrieve(ass_id)
            self.ai_assistants[assistant.id] = assistant

        if self.db:
            self.db.update_model(assistant)
        return assistant

    def get_thread(self, thread_id):
        """Gets thread from self or openai client if not retrieved yet"""
        thread = self.ai_threads.get(thread_id)

        if not thread:
            thread = self.client.beta.threads.retrieve(thread_id)
            self.ai_threads[thread_id] = thread

        if self.db:
            self.db.update_model(thread)
        return thread

    def update_assistant(self, ass_id, **kwargs):
        """Updates Assistant system_prompt/instructions and/or functions/tools"""
        assistant = self.client.beta.assistants.update(ass_id, **kwargs)

        if self.db:
            self.db.update_model(assistant)
        return assistant

    def add_message_to_thread(self, content, thread_id):
        """Add content to therad as user message"""

        role = "user"
        try:
            message = self.client.beta.threads.messages.create(thread_id=thread_id, content=content, role=role)
            if self.db:
                self.db.insert_model(message)
            return message

        except BadRequestError as e:
            print(f"BadRequestError: {e}")
            active_run_id = next((msg_part for msg_part in e.message.split() if "run_" in msg_part), None)
            if active_run_id:
                # Cancel the active Run and retry adding the message to the thread
                # since the Request contents did not trigger the BadRequestError
                self.cancel_run(active_run_id, thread_id)
                return self.add_message_to_thread(content, thread_id)

            # Request contents triggered the BadRequestError so raise the error
            raise e

    def cancel_run(self, run_id, thread_id):
        print(f"Canceling {run_id}")
        canceled_run = self.client.beta.threads.runs.cancel(run_id=run_id, thread_id=thread_id)
        print("Canceled Run", canceled_run)

        if self.db:
            self.db.update_model(canceled_run)

        return canceled_run

    def save_run_steps(self, run_id, thread_id):
        print(f"Saving run steps for run {run_id}")
        run_steps = self.client.beta.threads.runs.steps.list(run_id=run_id, thread_id=thread_id, limit=100, order="asc")

        if self.db:
            self.db.insert_models(*run_steps)

        return run_steps

    def wait_for_response(self, thread_id, run_id, sleep_interval=1, **kwargs):
        """
        Waits for a response and handles status updates.
        Calls handle_submit_tool_outputs_required to submit tool outputs when run requires action.
        Returns messages once recursive loop is complete.
        """
        run = None
        while not run or run.status in ("queued", "in_progress"):
            run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

            if self.db:
                self.db.update_model(run)

            print(f"Status: {run.status} Thread id: {thread_id}, run_id: {run_id}")

            if run.status == "requires_action":
                # Handles tool calls and submits tool outputs to run then recursively calls wait_for_response
                return self.handle_submit_tool_outputs_required(run, sleep_interval, **kwargs)

            if run.status in ("cancelled", "failed", "expired", "error") and run.last_error:
                self.save_run_steps(run_id, thread_id)
                raise RunStatusError(run.status, run.last_error)

            elif run.status == "completed":
                self.save_run_steps(run_id, thread_id)
                print(f"Run {run.id} completed")
                break

            else:
                print(f"Waiting {sleep_interval} seconds for response")
                sleep(sleep_interval)

        messages = self.client.beta.threads.messages.list(thread_id)
        if self.db:
            self.db.update_models(*messages)
        return messages

    def handle_submit_tool_outputs_required(self, run, sleep_interval=5, **kwargs):
        """Executes tool calls and submits tool outputs to run."""

        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            tool_name = tool_call.function.name
            arguments = json_loads(tool_call.function.arguments)

            print(f"\nAI called tool: {tool_name}\nwith args: {arguments}")
            # Get tool output with _do_tool_call
            tool_output = self._do_tool_call(tool_name, arguments, **kwargs)
            print(f"\nSubmitting tool output: {tool_output}")

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

    def _do_tool_call(self, tool_name, arguments, **kwargs):
        """Calls tool and returns output"""

        try:
            return self.tools[tool_name][1](arguments, **kwargs)
        except Exception as e:
            err_msg = f"Error getting tool output: {e}. Try again with different arguments."
            print(err_msg)
            return err_msg

    def run_with_assistant(
        self,
        *content,
        ass_id=None,
        thread_id=None,
        system_prompt=None,
        tool_names=None,
        sleep_interval=1,
        run_status_error_retries=1,
        **kwargs,
    ):
        """Runs prompt with Assistant, handles tool_calls and returns Assistant, Thread, Run, Messages"""

        # Get or create Assistant and Thread
        ass = self.get_assistant(ass_id) if ass_id else self.create_assistant()
        thread = self.get_thread(thread_id) if thread_id else self.create_thread()

        # To determine if Assitant needs to be updated when system_prompt or tools have changed
        update_kwargs = {}
        # Check if model has changed
        if self.model != ass.model:
            update_kwargs.update({"model": self.model})
        # Check if system_prompt/instructions have changed
        if system_prompt != ass.instructions:
            update_kwargs.update({"instructions": system_prompt})
        # Check for different tool names in tools argument and Assitants current tools
        tools = [self.tools[tool_name][0] for tool_name in (tool_names or ())]
        if tools != [tool.model_dump() for tool in ass.tools]:
            update_kwargs.update({"tools": tools})

        # Update Assitant if any update kwargs are present
        if update_kwargs:
            ass = self.update_assistant(ass.id, **update_kwargs)
            print(f"Updated {ass.id}: {', '.join(update_kwargs.keys())}")

        # Add content to thread as message(s)
        for message in content:
            self.add_message_to_thread(message, thread.id)

        # Create a run using the updated Assistant and Thread
        run = self.create_run(ass.id, thread.id, **kwargs)

        # Wait for messages and recursively handle tool_calls until run is complete or RunStatusError occurs
        try:
            messages = self.wait_for_response(thread.id, run.id, sleep_interval, **kwargs)

            print(f"Done {ass.id}, {thread.id}, {run.id}")
            return ass, thread, run, messages

        except RunStatusError as e:
            print(f"run_with_assistant caught: {e}")

            if run_status_error_retries > 0:
                print(f"Retrying {run_status_error_retries} more time(s)")

                return self.run_with_assistant(
                    *content,
                    ass_id=ass_id,
                    thread_id=thread_id,
                    system_prompt=system_prompt,
                    tool_names=tool_names,
                    sleep_interval=sleep_interval,
                    run_status_error_retries=run_status_error_retries - 1,
                    **kwargs,
                )

            raise e  # Raise the RunStatusError if no more retries
