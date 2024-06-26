from typing import Optional, Union, List
from datetime import datetime
from pydantic import BaseModel


class Question(BaseModel):
    question: str
    answer: Optional[str] = None
    choices: Optional[List[str]] = None


class Company(BaseModel):
    name: str
    url: Optional[str] = None
    industry: Optional[str] = None
    num_employees: Optional[str] = None
    num_employees_on_linkedin: Optional[str] = None
    description: Optional[str] = None


class HiringManager(BaseModel):
    name: str
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_name: Optional[str] = None


class Job(BaseModel):
    id: str
    title: str
    company: Optional[Company] = None
    location: Optional[str] = None
    url: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    min_hourly: Optional[float] = None
    max_hourly: Optional[float] = None
    pay_type: Optional[str] = None
    remote: Optional[bool] = None
    workplace_type: Optional[str] = None
    employment_type: Optional[str] = None
    seniority_level: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    hiring_manager: Optional[HiringManager] = None
    easy_apply: Optional[Union[bool, int]] = None
    date_posted: Optional[Union[datetime, str]] = None
    date_scraped: Optional[Union[datetime, str]] = None
    date_applied: Optional[Union[datetime, str]] = None
    status: Optional[str] = None
    num_applicants: Optional[str] = None

    def __hash__(self):
        return hash(self.id)
