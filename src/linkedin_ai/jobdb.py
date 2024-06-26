from typing import Set, Tuple
from .core.sqldantic import BaseDB, SQLDanticSchema
from .models import Job, Question


class JobAppDB(BaseDB):
    def create_tables(self) -> None:
        """Creates the tables to store Job, Company, HiringManager, and Question models."""
        self.create_tables_from_models(Job, Question)

    def get_all_job_ids(self) -> Set[str]:
        """Get all job ids from the jobs table with a direct SQL query."""
        query = "SELECT id FROM jobs"
        self.execute_and_commit(query, ())
        return set(row[0] for row in self.cursor.fetchall())

    @staticmethod
    def select_questions_or_answer_like_keyword(
        sqldantic_schema: SQLDanticSchema, *args
    ) -> Tuple[str, Tuple[str, ...]]:
        """A select query factory that returns a query to select questions or answers that contain any of the given keywords."""
        condition_clause = " OR ".join("question LIKE ?" for arg in args)
        condition_clause += " OR " + " OR ".join("answer LIKE ?" for arg in args)
        values = tuple(f"%{arg}%" for arg in args) * 2
        query = f"SELECT * FROM {sqldantic_schema.table_name} WHERE {condition_clause}"
        return query, values

    def get_questions_containing_keywords(self, *keywords):
        """Get all questions that contain any of the given keywords."""
        return self.get_models(
            Question,
            *keywords,
            select_query_factory=self.select_questions_or_answer_like_keyword,
        )
