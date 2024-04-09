from typing import Union, Optional, Dict, Tuple, Callable
from pathlib import Path
from datetime import datetime

from core.aimanager import OpenAIManager
from jobdb import JobAppDB
from models import Question


class JobAppAI(OpenAIManager):
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

            print(f"\n Done with: {question.question}\nAnswer: {answer}")

        return questions
