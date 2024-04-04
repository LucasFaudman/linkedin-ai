
from pathlib import Path
from typing import Union, Iterator, Iterable, Optional, Callable
from time import sleep
from datetime import datetime, timedelta

from core.souperscraper import SouperScraper, Keys
from jobdb import JobAppDB
from jobai import JobAppAI
from models import Job, Company, HiringManager, Question


def parse_relative_date(date_str: str) -> datetime:
    if date_str.startswith("Reposted "):
        date_str = date_str[9:]

    today = datetime.now()
    int_val = int(date_str.split()[0])
    for time_unit in ("minute", "hour", "day", "week", "month"):
        if time_unit in date_str:
            if time_unit == "month":
                int_val *= 30
                time_unit = "day"
            return today - timedelta(**{time_unit + "s": int_val})
    raise ValueError("Unsupported relative date format")


class LinkedInAutomator:

    def __init__(self,
                 webdriver_path: str,
                 li_username: Optional[str] = None,
                 li_password: Optional[str] = None,
                 resume_path: Union[str, Path] = "resume_path.txt",
                 job_app_db_path: Union[str, Path] = "jobs.db",
                 ai_db_path: Union[str, Path] = "ai.db",
                 assistant_id=None,
                 thread_id=None,
                 api_key="OPENAI_API_KEY",
                 model="gpt-3.5-turbo",
                 ):

        self.webdriver_path = webdriver_path
        self.li_username = li_username
        self.li_password = li_password
        self.resume = (resume_path if isinstance(
            resume_path, Path) else Path(resume_path)).read_text()
        self.job_app_db_path = job_app_db_path
        self.job_app_db = None
        self.ai_db_path = ai_db_path if isinstance(
            ai_db_path, Path) else Path(ai_db_path)
        self.ai = None
        self.assistant_id = assistant_id
        self.thread_id = thread_id
        self.api_key = api_key
        self.model = model

    def init_dbs(self):
        self.job_app_db = JobAppDB(self.job_app_db_path)
        self.job_app_db.create_tables()
        self.seen_job_ids = self.job_app_db.get_all_job_ids()

        self.ai = JobAppAI(
            resume=self.resume,
            job_app_db=self.job_app_db,
            ai_db_path=self.ai_db_path,
            assistant_id=self.assistant_id,
            thread_id=self.thread_id,
            api_key=self.api_key,
            model=self.model
        )

    def close_dbs(self):
        if self.job_app_db:
            self.job_app_db.close_connection()
        if self.ai and self.ai.db:
            self.ai.db.close_connection()

    def init_scraper(self):
        self.scraper = SouperScraper(executable_path=self.webdriver_path)

    def close_scraper(self):
        if self.scraper:
            self.scraper.quit()

    def goto_login(self):
        linkendin_login_url = "https://www.linkedin.com/login"
        if self.scraper.current_url != linkendin_login_url:
            self.scraper.goto(linkendin_login_url, sleep_secs=2)

    def login(self, li_username=None, li_password=None):
        li_username = li_username or self.li_username
        li_password = li_password or self.li_password
        self.goto_login()
        self.scraper.find_element_by_id("username").send_keys(li_username)
        self.scraper.find_element_by_id("password").send_keys(li_password)
        self.scraper.find_element_by_css_selector(
            "button[type='submit']").click()
        if not self.scraper.wait_until_url_contains("/feed/"):
            return False
        return True

    def get_filtered_search_url(self, filters: dict) -> str:
        base_url = "https://www.linkedin.com/jobs/search/?"
        filter_names_map = {
            "search_term": "keywords",
            "location": "location",
            "Distance": "distance",
            'Sort by': 'sortBy',
            "Date posted": "f_TPR",
            "Experience level": "f_E",
            "Job type": "f_JT",
            "Remote": "f_WT",
            "Easy Apply": "f_AL",
            "Under 10 applicants": "f_EA",
            "Fair Chance Employer": "f_FCE",
            "Salary": "f_SB2",

        }
        filter_values_map = {
            "Sort by": {"Most relevant": "R", "Most recent": "DD"},
            "Date posted": {"Past 24 hours": "r86400", "Past week": "r604800", "Past month": "r2592000"},
            "Experience level": {"Internship": "1", "Entry level": "2", "Associate": "3", "Mid-Senior level": "4", "Director": "5", "Executive": "6"},
            "Job type": {"Full-time": "F", "Part-time": "P", "Contract": "C", "Volunteer": "V", "Other": "O"},
            "Remote": {"On-site": "1", "Remote": "2", "Hybrid": "3"},
            "Salary": {"$40,000+": "1", "$60,000+": "2", "$80,000+": "3", "$100,000+": "4", "$120,000+": "5", "$140,000+": "6", "$160,000+": "7", "$180,000+": "8", "$200,000+": "9"}
        }

        filters["Distance"] = filters.get('Distance', '5').split()[0]
        params = {}
        for filter_name, filter_value in filters.items():
            if filter_name in filter_names_map:
                if filter_name in filter_values_map:
                    filter_value_map = filter_values_map[filter_name]
                    if isinstance(filter_value, list):
                        filter_value = '%2C'.join(
                            (filter_value_map[value] for value in filter_value if value in filter_value_map))
                    else:
                        filter_value = filter_value_map.get(filter_value)
                elif filter_value == True:
                    filter_value = "true"

                if not filter_value:
                    continue

                params[filter_names_map[filter_name]] = filter_value

        params.update({
            "origin": "JOB_SEARCH_PAGE_JOB_FILTER",
            "refresh": "true",
            "spellCorrectionEnabled": "true"
        })

        search_url = base_url + \
            "&".join(f"{key}={value}" for key, value in params.items())
        return search_url

    def iter_jobs(self, filters: dict) -> Iterator[Job]:
        self.scraper.goto(self.get_filtered_search_url(filters), sleep_secs=3)
        more_jobs = True
        while more_jobs:
            for job in self.get_jobs_from_search():
                if job.id not in self.seen_job_ids:
                    self.seen_job_ids.add(job.id)
                    yield job

            more_jobs = self.click_next_page()

    def click_button_with_aria_label(self, label=""):
        self.scraper.find_element_by_css_selector(
            f"button[aria-label='{label}']").click()

    def click_next_page(self) -> bool:
        current_page = None
        for page in filter(
                lambda elm: elm.attrs['aria-label'].startswith('Page'),
                self.scraper.soup.find_all('button', attrs={'aria-label': True})):

            if page.attrs.get('aria-current'):
                current_page = page.attrs['aria-label']
            elif current_page:
                page_button_label = page.attrs['aria-label']
                self.click_button_with_aria_label(page_button_label)
                sleep(2)
                return True

        return False

    def get_jobs_from_search(self) -> Iterator[Job]:
        for job_card in self.scraper.soup.find_all('div', attrs={'data-job-id': lambda x: isinstance(x, str) and x.isdigit(), 'data-view-name': 'job-card'}):
            job_id = job_card.attrs['data-job-id']
            link_elm = job_card.find('a')
            title = link_elm.text.strip()
            url = 'https://www.linkedin.com/jobs/view/' + job_id + "/"
            company_name = job_card.find(
                'span', attrs={'class': 'job-card-container__primary-description'}).text.strip()
            location = job_card.find(
                'li', attrs={'class': 'job-card-container__metadata-item'}).text.strip()
            if "(" in location:
                location, workplace_type = location.split("(", 1)
                location = location.strip()
                workplace_type = workplace_type.strip(")").strip()
                remote = (workplace_type == "Remote")
            else:
                workplace_type = None
                remote = None

            yield Job(id=job_id, title=title, company=Company(name=company_name), location=location, url=url, remote=remote, workplace_type=workplace_type)

    def goto_job(self, job: Job, sleep_secs=0) -> Job:
        if self.scraper.current_url != job.url:
            self.scraper.goto(job.url, sleep_secs)

        return job

    def update_job(self, job: Job) -> Job:
        self.goto_job(job, sleep_secs=3)
        soup = self.scraper.soup

        if ((details_container := soup.find('div', attrs={'class': 'job-details-jobs-unified-top-card__primary-description-container'}))
                and "·" in details_container.text):

            company_name, location, date_posted, num_applicants = map(
                str.strip, details_container.text.split("·"))
            company_dict = {"name": company_name}

            job.location = location
            job.date_posted = parse_relative_date(date_posted)
            job.num_applicants = num_applicants

            if a_elm := details_container.find('a', attrs={'href': True}):
                company_dict["url"] = a_elm.attrs['href']

            if company_container := soup.find('div', attrs={'class': 'jobs-company__box'}):
                company_dict["description"] = company_container.find(
                    'p', attrs={'class': 'jobs-company__company-description'}).text.strip()

                if company_details := company_container.find('div', attrs={'class': 't-14'}):
                    company_dict["industry"], company_dict["num_employees"], company_dict["num_employees_on_linkedin"] = [
                        s.strip() for s in company_details.text.strip().split('\n') if s.strip()]

            job.company = Company(**company_dict)

        if ((insights_container := soup.find('li', attrs={'class': 'job-details-jobs-unified-top-card__job-insight--highlight'}))
                and (insights := insights_container.find('span'))):
            for elm in insights:
                if stripped_text := elm.text.strip():
                    if "workplace type is" in stripped_text:
                        job.workplace_type = stripped_text.split(
                        )[-1].strip('.')
                        job.remote = True if job.workplace_type == "Remote" else False
                    elif "job type is" in stripped_text:
                        job.employment_type = stripped_text.split(
                        )[-1].strip('.')
                    elif "/" not in stripped_text:
                        job.seniority_level = stripped_text

        if hirer_card := soup.find('div', attrs={'class': 'hirer-card__hirer-information'}):
            job.hiring_manager = HiringManager(
                name=hirer_card.find(
                    'span', attrs={'class': 'jobs-poster__name'}).text.strip(),
                title=hirer_card.find(
                    'div', attrs={'class': 'hirer-card__hirer-job-title'}).text.strip(),
                linkedin_url=hirer_card.find(
                    'a', attrs={'href': True}).attrs['href'],
                company_name=job.company.name
            )
        if description_container := soup.find('div', attrs={'id': 'job-details'}):
            job.description = description_container.text.replace(
                'About the job', '').replace('About Us', '').strip()

        if salary_container := soup.find('div', attrs={'id': 'SALARY'}):
            if ((salary_div := salary_container.find('div', attrs={'class': 'mt4'}))
                    and (salary_p := salary_div.find('p'))):
                pay_range = [s.replace('$', '').replace(',', '')
                             for s in salary_p.text.strip().split() if "/" in s]
                min_pay = pay_range[0]
                if len(pay_range) > 1:
                    max_pay = pay_range[1]
                else:
                    max_pay = min_pay

                if "/hr" in min_pay:
                    job.min_hourly = float(min_pay[:-3])
                    job.max_hourly = float(max_pay[:-3])
                    job.min_salary = job.min_hourly * 40 * 50
                    job.max_salary = job.max_hourly * 40 * 50
                    job.pay_type = "hourly"
                elif "/yr" in min_pay:
                    job.min_salary = float(min_pay[:-3])
                    job.max_salary = float(max_pay[:-3])
                    job.min_hourly = job.min_salary / (40 * 50)
                    job.max_hourly = job.max_salary / (40 * 50)
                    job.pay_type = "salary"

            if benefits_items := salary_container.find_all('li', attrs={'class': 'featured-benefits__benefit'}):
                job.benefits = [elm.text.strip() for elm in benefits_items]

        if skills_items := soup.find_all('a', attrs={'class': 'job-details-how-you-match__skills-item-subtitle'}):
            job.skills = []
            for elm in skills_items:
                for skill in elm.text.strip().split(","):
                    skill = skill.strip()
                    if skill.startswith("and "):
                        skill = skill[4:]
                    job.skills.append(skill)

        if apply_button := soup.find('div', attrs={'class': 'jobs-apply-button--top-card'}):
            job.easy_apply = "Easy Apply" in apply_button.text
            # TODO check if job is already applied to and set status to "applied" if it is

        job.date_scraped = datetime.now()
        if not job.status:
            job.status = 'scraped'
        self.job_app_db.insert_model(job)
        return job

    def apply_to_job(self, job: Job):
        job = self.update_job(job)
        self.scraper.wait_for_visibility_of_element_located_by_class_name(
            "jobs-apply-button--top-card").click()

        status = "incomplete"
        while (soup := self.scraper.soup) and not soup.find('button', attrs={'aria-label': 'Submit application'}):
            try:
                for input_elm, question in self.get_questions():
                    # Get the answer from the DB if it exists
                    if (saved_question := self.job_app_db.get_model(Question, question.question)) and saved_question.answer:
                        question.answer = saved_question.answer
                    else:
                        # Or add it to the DB if it doesn't exist yet and ask the AI or user for an answer
                        self.job_app_db.insert_model(question)

                    if not question.answer:
                        question = self.answer_job_question(question)
                        if not question.answer:
                            status = "needs answer"
                            break
                        self.job_app_db.update_model(question)

                        if isinstance(input_elm, dict):
                            input_elm = input_elm[question.answer]

                        self.scraper.scroll_to(input_elm)
                        input_elm.click()

                        try:
                            # TODO test w/ https://www.linkedin.com/jobs/view/3815139746/
                            input_elm.send_keys(question.answer)
                            input_elm.send_keys(Keys.RETURN)
                        except Exception as e:
                            print(
                                f"Failed to send keys to element. Ignoring error: {e}")

                if upload_elms := soup.find_all('label', attrs={'class': 'jobs-document-upload__upload-button'}):
                    for upload_elm in upload_elms:
                        if 'Upload cover letter' in upload_elm.text:
                            status = "needs cover letter"

                if status in ("needs answer", "needs cover letter"):
                    break

                if soup.find('button', attrs={'aria-label': 'Continue to next step'}):
                    self.click_button_with_aria_label("Continue to next step")

                elif soup.find('button', attrs={'aria-label': "Review your application"}):
                    self.click_button_with_aria_label(
                        "Review your application")

            except Exception as e:
                print(f"Failed to answer questions. Error: {e}")
                status = "error"
                break

        if soup.find('button', attrs={'aria-label': 'Submit application'}):
            status = "complete"

        if status != "complete":
            print(
                f"Failed to apply to job {job.title} at {job.company.name} in {job.location}. Status: {status}")
            job.status = status
            self.job_app_db.update_model(job)
            # Close and save the application for later
            self.click_button_with_aria_label("Dismiss")
            self.scraper.find_element_by_css_selector(
                f"button[data-control-name='save_application_btn']").click()
            return job

        try:
            self.scraper.find_element_by_css_selector(
                "label[for='follow-company-checkbox']").click()
        except Exception as e:
            print(f"Failed to unfollow company. Ignoring. Error: {e}")

        self.click_button_with_aria_label("Submit application")
        job.status = "applied"
        job.date_applied = datetime.now()
        self.job_app_db.update_model(job)
        print(
            f"Applied to job {job.title} at {job.company.name} in {job.location}")
        return job

    def get_questions(self):
        question_count = 0
        for form_elm in self.scraper.find_elements_by_class_name('jobs-easy-apply-form-section__grouping'):
            # Simple text input
            for container_elm, input_elm in zip(
                form_elm.find_elements(
                    'class name', 'artdeco-text-input--container'),
                form_elm.find_elements(
                    'class name', 'artdeco-text-input--input')
            ):
                question_text = container_elm.text
                current_val = input_elm.get_attribute('value')
                question_count += 1
                yield input_elm, Question(question=question_text, answer=current_val, choices=None)

            # TODO Test with https://www.linkedin.com/jobs/view/3864508460/
            # Textarea multi-line input
            for textarea in form_elm.find_elements('tag name', 'textarea'):
                question_text = textarea.get_attribute('aria-label')
                current_val = textarea.get_attribute('value')
                question_count += 1
                yield textarea, Question(question=question_text, answer=current_val, choices=None)

            # Dropdown selection
            for select_elm in form_elm.find_elements('tag name', 'select'):
                question_text = select_elm.accessible_name
                choices = [elm.accessible_name for elm in select_elm.find_elements(
                    "tag name", "option")[1:]]
                current_val = value if (value := select_elm.get_attribute(
                    'value')) != "Select an option" else None
                if question_text != "Select Language":
                    question_count += 1
                    yield select_elm, Question(question=question_text, answer=current_val, choices=choices)

            # Form input with choices (radio, checkbox, etc.)
            for form_label in form_elm.find_elements('class name', 'fb-dash-form-element__label'):
                question_text = form_label.find_element(
                    'tag name', 'span').text
                # Label refers to input element by id and input is interactable
                if input_id := form_label.get_attribute('for'):
                    input_elm = form_elm.find_element('id', input_id)
                    current_val = input_elm.get_attribute('value')
                    question_count += 1
                    yield input_elm, Question(question=question_text, answer=current_val, choices=None)

                else:
                    # Each choice is a separate label/input element pair, but the input is not interactable, the label is
                    choices = []
                    input_elms = {}
                    for select_elm in form_elm.find_elements('class name', 'fb-text-selectable__option'):
                        choice = select_elm.text
                        choices.append(choice)
                        input_elms[choice] = select_elm.find_element(
                            'tag name', 'label')

                    question_count += 1
                    yield input_elms, Question(question=question_text, answer=None, choices=choices)

        if question_count == 0:
            print("Failed to find input element for question. Skipping")

        return question_count

    def get_filter_options(self, search_term: str):
        self.scraper.goto(
            f"https://www.linkedin.com/jobs/search/?keywords={search_term}", sleep_secs=3)
        self.click_button_with_aria_label(
            'Show all filters. Clicking this button displays all available filter options.')
        self.scraper.wait_for_visibility_of_element_located_by_id(
            "reusable-search-advanced-filters-right-panel")

        filters = {}
        for filter_container in self.scraper.soup.find_all('li', attrs={'class': 'search-reusables__secondary-filters-filter'}):
            filter_name = filter_container.find('h3').text.strip()
            if filter_container.find('div', attrs={'class': 'search-reusables__advanced-filters-binary-toggle'}):
                filter_type = "toggle"

            choices = []
            for choice in filter_container.find_all('li', attrs={'class': 'search-reusables__filter-value-item'}):
                choice_text = choice.text.strip().split('\n')[0]
                if choice_text.startswith("Add a"):
                    continue
                choices.append(choice_text)
                if input_elm := choice.find('input'):
                    filter_type = input_elm.attrs['type']

            filters[filter_name] = (filter_type, choices)

        self.click_button_with_aria_label('Dismiss')
        return filters

    def _try_func_on_jobs_in_new_tab(self, jobs_iter: Iterable[Job], func: Callable[[Job], Job], close_tab_after=True) -> Iterator[Job]:
        initial_tab = self.scraper.current_tab
        for job in jobs_iter:
            print(
                f"Tying {job.id}: {job.title} at {job.company.name} in {job.location}")
            try:
                self.scraper.new_tab()
                self.scraper.switch_to_tab(index=-1)
                yield func(job)
            except Exception as e:
                print(
                    f"Failed {job.id}: {job.title} at {job.company.name} in {job.location}. Error: {e}")

            if close_tab_after:
                try:
                    self.scraper.close()
                except Exception as e:
                    print(f"Failed to close tab. Error: {e}")

                try:
                    self.scraper.switch_to_tab(window_handle=initial_tab)
                except Exception as e:
                    print(f"Failed to switch back to initial tab. Error: {e}")

    def apply_to_jobs(self, jobs_iter: Iterable[Job]) -> Iterator[Job]:
        return self._try_func_on_jobs_in_new_tab(jobs_iter, self.apply_to_job)

    def update_jobs(self, jobs_iter: Iterable[Job]) -> Iterator[Job]:
        return self._try_func_on_jobs_in_new_tab(jobs_iter, self.update_job)

    def open_jobs(self, jobs_iter: Iterable[Job]) -> Iterator[Job]:
        return self._try_func_on_jobs_in_new_tab(jobs_iter, self.goto_job, close_tab_after=False)

    def answer_job_question(self, question: Question) -> Question:
        # Otherwise have the AI answer the question
        question, *_ = self.ai.answer_job_questions(question)
        return question
