from core.sqldantic import BaseDB, SQLDanticSchema
from models import Job, Question


class JobAppDB(BaseDB):

    def create_tables(self) -> None:
        self.create_tables_from_models(Job, Question)

    def get_all_job_ids(self) -> set[str]:
        query = "SELECT id FROM jobs"
        self.execute_and_commit(query, ())
        return set(row[0] for row in self.cursor.fetchall())

    @staticmethod
    def select_questions_or_answer_like_keyword(sqldantic_schema: SQLDanticSchema, *args):
        condition_clause = " OR ".join(f"question LIKE ?" for arg in args)
        condition_clause += " OR " + \
            " OR ".join(f"answer LIKE ?" for arg in args)
        values = tuple(f"%{arg}%" for arg in args) * 2
        query = f"SELECT * FROM {sqldantic_schema.table_name} WHERE {condition_clause}"
        return query, values

    def get_questions_containing_keywords(self, *keywords):
        return self.get_models(Question, *keywords, select_query_factory=self.select_questions_or_answer_like_keyword)
