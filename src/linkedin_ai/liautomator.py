from typing import Optional, Union, Iterator, Iterable, Callable, Literal, Tuple, Dict
from pathlib import Path
from time import sleep
from datetime import datetime, timedelta

from souperscraper import SouperScraper, Keys, WebElement
from .jobdb import JobAppDB
from .jobai import JobAppAI
from .models import Job, Company, HiringManager, Question


def parse_relative_date(date_str: str) -> datetime:
    """
    Converts a relative date string from LinkedIn to a datetime object.
    E.g. '2 days ago', 'Reposted 1 week ago', etc.
    """
    if date_str.startswith("Reposted "):
        date_str = date_str[9:]

    today = datetime.now()
    int_val = int(date_str.split()[0])
    for time_unit in ("minute", "hour", "day", "week", "month"):
        if time_unit in date_str:
            if time_unit == "month":
                int_val *= 30  # Approximate months to days
                time_unit = "day"
            return today - timedelta(**{time_unit + "s": int_val})
    raise ValueError("Unsupported relative date format")


class LinkedInAutomator:
    """
    Engine for automating LinkedIn
    built with:
    - SouperScraper: Scrapes and interacts with LinkedIn using Selenium for dynamic interaction and BeautifulSoup4 for static HTML parsing
    - JobAppDB (SQLDantic BaseDB): Creates the SQLite database for storing Job, Company, HiringManager, and Question pydantic models
    - JobAppAI (OpenAIManager): Uses OpenAI's Assistant API to answer job application questions, generate cover letters, etc.
    """

    def __init__(
        self,
        li_username: Optional[str] = None,
        li_password: Optional[str] = None,
        resume_path: Union[str, Path] = "resume.txt",
        default_cover_letter_path: Optional[Union[str, Path]] = None,
        cover_letter_output_dir: Union[str, Path] = "./cover-letters/",
        cover_letter_action: Literal["skip", "default", "generate"] = "skip",
        job_app_db_path: Union[str, Path] = "jobs.db",
        ai_db_path: Union[str, Path] = "ai.db",
        assistant_id=None,
        thread_id=None,
        api_key="OPENAI_API_KEY",
        model="gpt-3.5-turbo",
        webdriver_path: str = "./chromedriver",
        user_agent=None,
        proxy=None,
    ):
        # LinkedIn login credentials
        self.li_username = li_username
        self.li_password = li_password

        # resume_path is handled as a Path and text is read from the file.
        resume_path = resume_path if isinstance(resume_path, Path) else Path(resume_path)
        self.resume = resume_path.read_text()

        # default_convert_letter_path is handled as a str since it is used later with input_elm.send_keys()
        self.default_cover_letter_path = (
            default_cover_letter_path if isinstance(default_cover_letter_path, str) else str(default_cover_letter_path)
        )
        self.cover_letter_action = cover_letter_action

        # cover_letter_output_dir is handled as a Path object
        self.cover_letter_output_dir = (
            cover_letter_output_dir if isinstance(cover_letter_output_dir, Path) else Path(cover_letter_output_dir)
        )

        # Both job_app_db_path and ai_db_path are handled as Path objects
        self.job_app_db_path = job_app_db_path if isinstance(job_app_db_path, Path) else Path(job_app_db_path)
        self.ai_db_path = ai_db_path if isinstance(ai_db_path, Path) else Path(ai_db_path)

        # These are initialized in init_dbs() so this can be used in separate threads from the thread that initializes the object
        self.job_app_db = None
        self.ai = None
        self.seen_job_ids = set()

        # OpenAI API credentials and settings for the JobAppAI object
        self.assistant_id = assistant_id
        self.thread_id = thread_id
        self.api_key = api_key
        self.model = model

        # WebDriver settings for the SouperScraper
        self.webdriver_path = webdriver_path
        self.user_agent = user_agent
        self.proxy = proxy

    def init_dbs(self):
        """Initializes the JobAppDB and JobAppAI objects (and the underlying AI db)."""

        # Initialize the JobAppDB object and create the tables if the db file doesn't exist
        new_job_app_db = not self.job_app_db_path.exists()
        self.job_app_db = JobAppDB(self.job_app_db_path)
        if new_job_app_db:
            self.job_app_db.create_tables()

        # Update the seen_job_ids set with all the job ids in the db
        self.seen_job_ids |= self.job_app_db.get_all_job_ids()

        # Initialize the JobAppAI object (and the underlying AI db if a path is provided)
        self.ai = JobAppAI(
            job_app_db=self.job_app_db,
            ai_db_path=self.ai_db_path,
            assistant_id=self.assistant_id,
            thread_id=self.thread_id,
            api_key=self.api_key,
            model=self.model,
            resume=self.resume,
            cover_letter_output_dir=self.cover_letter_output_dir,
            cover_letter_start_text="Dear Hiring Manager,",
            cover_letter_end_text="Sincerely, <Candidate Name>",
            cover_letter_example_texts=None,
        )

    def close_dbs(self):
        """Closes the JobAppDB and JobAppAI underlying db connections."""
        try:
            if self.job_app_db:
                self.job_app_db.close_connection()
        except Exception as e:
            print(f"Failed to close JobAppDB connection. Error: {e}")
        finally:
            self.job_app_db = None

        try:
            if self.ai and self.ai.db:
                self.ai.db.close_connection()
        except Exception as e:
            print(f"Failed to close JobAppAI db connection. Error: {e}")
        finally:
            self.ai = None

    def init_scraper(self):
        """Initializes the SouperScraper object for scraping LinkedIn using the provided WebDriver settings."""
        self.scraper = SouperScraper(
            executable_path=self.webdriver_path,
            user_agent=self.user_agent,
            proxy=self.proxy,
        )

    def close_scraper(self):
        """Quits the SouperScraper object if it exists."""
        if self.scraper:
            self.scraper.quit()

    def goto_login(self):
        """Navigates to the LinkedIn login page and sleeps for 2 seconds to allow page to load."""
        linkendin_login_url = "https://www.linkedin.com/login"
        if self.scraper.current_url != linkendin_login_url:
            self.scraper.goto(linkendin_login_url, sleep_secs=1.5)

    def login(self, li_username: Optional[str] = None, li_password: Optional[str] = None) -> bool:
        """Logs into LinkedIn using the provided credentials or the ones provided in the constructor."""
        # Use the provided credentials or the ones provided in the constructor
        li_username = li_username or self.li_username
        li_password = li_password or self.li_password
        self.goto_login()  # Navigate to the login page

        # Fill in the username and password fields and click the submit button
        self.scraper.find_element_by_id("username").send_keys(li_username)
        self.scraper.find_element_by_id("password").send_keys(li_password)
        self.scraper.find_element_by_css_selector("button[type='submit']").click()

        # Wait for the page to load and check if the login was successful
        if not self.scraper.wait_until_url_contains("/feed/"):
            # If not redirected to the feed, captcha, incorrect credentials, etc then the login failed
            return False
        return True

    def get_filter_options(self, search_term: str):
        """Gets the filter options available for a LinkedIn job search."""
        self.scraper.goto(
            f"https://www.linkedin.com/jobs/search/?keywords={search_term}",
            sleep_secs=1.5,
        )
        self.click_button_with_aria_label(
            "Show all filters. Clicking this button displays all available filter options."
        )
        self.scraper.wait_for_visibility_of_element_located_by_id("reusable-search-advanced-filters-right-panel")

        filters = {}
        for filter_container in self.scraper.soup.find_all(
            "li", attrs={"class": "search-reusables__secondary-filters-filter"}
        ):
            filter_name = filter_container.find("h3").text.strip()
            if filter_container.find(
                "div",
                attrs={"class": "search-reusables__advanced-filters-binary-toggle"},
            ):
                filter_type = "toggle"

            choices = []
            for choice in filter_container.find_all("li", attrs={"class": "search-reusables__filter-value-item"}):
                choice_text = choice.text.strip().split("\n")[0]
                if choice_text.startswith("Add a"):
                    continue
                choices.append(choice_text)
                if input_elm := choice.find("input"):
                    filter_type = input_elm.attrs["type"]

            filters[filter_name] = (filter_type, choices)

        self.click_button_with_aria_label("Dismiss")
        return filters

    def get_collections(self):
        """Gets the available LinkedIn job collections."""
        self.scraper.goto("https://www.linkedin.com/jobs/collections/", sleep_secs=1.5)
        collections = {}
        for collection_elm in self.scraper.soup.find_all("li", attrs={"class": "jobs-search-discovery-tabs__listitem"}):
            collection_name = collection_elm.text.strip()
            collection_url = collection_elm.find("a").attrs["href"]
            collection_tag = collection_url.split("/")[-1].split("?")[0].strip()
            collections[collection_name] = collection_tag
        return collections

    def get_filtered_search_url(self, filters: dict) -> str:
        """Generates a LinkedIn job search URL with the provided filters."""
        base_url = "https://www.linkedin.com/jobs/"
        if collection := filters.pop("collection", None):
            base_url += f"collections/{collection}/?"
        else:
            base_url += "search/?"

        filter_names_map = {
            "search_term": "keywords",
            "location": "location",
            "Distance": "distance",
            "Sort by": "sortBy",
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
            "Date posted": {
                "Past 24 hours": "r86400",
                "Past week": "r604800",
                "Past month": "r2592000",
            },
            "Experience level": {
                "Internship": "1",
                "Entry level": "2",
                "Associate": "3",
                "Mid-Senior level": "4",
                "Director": "5",
                "Executive": "6",
            },
            "Job type": {
                "Full-time": "F",
                "Part-time": "P",
                "Contract": "C",
                "Volunteer": "V",
                "Other": "O",
            },
            "Remote": {"On-site": "1", "Remote": "2", "Hybrid": "3"},
            "Salary": {
                "$40,000+": "1",
                "$60,000+": "2",
                "$80,000+": "3",
                "$100,000+": "4",
                "$120,000+": "5",
                "$140,000+": "6",
                "$160,000+": "7",
                "$180,000+": "8",
                "$200,000+": "9",
            },
        }

        filters["Distance"] = filters.get("Distance", "5").split()[0]
        params = {}
        for filter_name, filter_value in filters.items():
            if filter_name in filter_names_map:
                if filter_name in filter_values_map:
                    filter_value_map = filter_values_map[filter_name]
                    if isinstance(filter_value, list):
                        filter_value = "%2C".join(
                            (filter_value_map[value] for value in filter_value if value in filter_value_map)
                        )
                    else:
                        filter_value = filter_value_map.get(filter_value)
                elif filter_value == True:
                    filter_value = "true"

                if not filter_value:
                    continue

                params[filter_names_map[filter_name]] = filter_value

        if collection:
            params["discover"] = "recommended"
            params["discoveryOrigin"] = "PUBLIC_COMMS"
        else:
            params["origin"] = "JOB_SEARCH_PAGE_JOB_FILTER"
            params["refresh"] = "true"
            params["spellCorrectionEnabled"] = "true"

        search_url = base_url + "&".join(f"{key}={value}" for key, value in params.items())
        return search_url

    def iter_jobs(self, filters: dict) -> Iterator[Job]:
        """Iterates over the jobs on the LinkedIn search page with the provided filters."""
        # Navigate to the LinkedIn job search page with the provided filters or collection
        if filters:
            search_url = self.get_filtered_search_url(filters)
            self.scraper.goto(search_url, sleep_secs=1.5)

        more_jobs = True
        while more_jobs:
            # Yield all new jobs on the current page
            for job in self.get_jobs_from_search():
                if job.id not in self.seen_job_ids:
                    self.seen_job_ids.add(job.id)
                    yield job

            # There are more jobs if the next page button is clicked successfully
            more_jobs = self.click_next_page()

    def click_button_with_aria_label(self, label="") -> None:
        """Clicks a button on the LinkedIn page with the provided aria-label."""
        self.scraper.find_element_by_css_selector(f"button[aria-label='{label}']").click()

    def click_next_page(self) -> bool:
        """Attempts to click the next page button on the LinkedIn search page. Returns True if successful, False otherwise."""
        current_page = None
        for page in filter(
            lambda elm: elm.attrs["aria-label"].startswith("Page"),
            self.scraper.soup.find_all("button", attrs={"aria-label": True}),
        ):
            if page.attrs.get("aria-current"):
                current_page = page.attrs["aria-label"]
            elif current_page:
                page_button_label = page.attrs["aria-label"]
                self.click_button_with_aria_label(page_button_label)
                sleep(2)
                return True

        return False

    def get_jobs_from_search(self) -> Iterator[Job]:
        """Yields Job objects from the current LinkedIn search page."""

        for job_card in self.scraper.soup.find_all(
            "div",
            attrs={
                "data-job-id": lambda x: isinstance(x, str) and x.isdigit(),
                "data-view-name": "job-card",
            },
        ):
            job_id = job_card.attrs["data-job-id"]
            link_elm = job_card.find("a")
            title = link_elm.text.strip()
            title = title[: len(title) // 2]
            url = "https://www.linkedin.com/jobs/view/" + job_id + "/"
            company_name = job_card.find(
                "span", attrs={"class": "job-card-container__primary-description"}
            ).text.strip()
            location = job_card.find("li", attrs={"class": "job-card-container__metadata-item"}).text.strip()
            if "(" in location:
                location, workplace_type = location.split("(", 1)
                location = location.strip()
                workplace_type = workplace_type.strip(")").strip()
                remote = workplace_type == "Remote"
            else:
                workplace_type = None
                remote = None

            yield Job(
                id=job_id,
                title=title,
                company=Company(name=company_name),
                location=location,
                url=url,
                remote=remote,
                workplace_type=workplace_type,
            )

    def goto_job(self, job: Job, sleep_secs=0) -> Job:
        """Navigates to the LinkedIn job page for the provided Job object."""
        if self.scraper.current_url != job.url:
            self.scraper.goto(job.url, sleep_secs)
        return job

    def update_job(self, job: Job) -> Job:
        """Updates the Job object with details from the LinkedIn job page."""
        # Add the job to the db if it doesn't exist and navigate to the job page
        self.job_app_db.insert_model(job)
        self.goto_job(job, sleep_secs=1.5)

        # BeautifulSoup4 is used to parse the static HTML of the job page
        soup = self.scraper.soup

        company_dict = {}
        if company_name_elm := soup.find("div", attrs={"class": "job-details-jobs-unified-top-card__company-name"}):
            company_dict["name"] = company_name_elm.text.strip()

        # Job and company details
        if (
            details_container := soup.find(
                "div",
                attrs={"class": "job-details-jobs-unified-top-card__primary-description-container"},
            )
        ) and "·" in details_container.text:
            details = [detail.strip() for detail in details_container.text.split("·")]
            location, date_posted = details[:2]

            job.location = location
            job.date_posted = parse_relative_date(date_posted)
            if len(details) > 2:
                num_applicants = details[2]
                if num_applicants.endswith("applicants"):
                    job.num_applicants = num_applicants

            if a_elm := details_container.find("a", attrs={"href": True}):
                company_dict["url"] = a_elm.attrs["href"]

            if company_container := soup.find("div", attrs={"class": "jobs-company__box"}):
                company_dict["description"] = company_container.find(
                    "p", attrs={"class": "jobs-company__company-description"}
                ).text.strip()

                if company_details := company_container.find("div", attrs={"class": "t-14"}):
                    details = [s.strip() for s in company_details.text.strip().split("\n") if s.strip()]
                    for detail in details:
                        if "employees" in detail:
                            company_dict["num_employees"] = detail
                        elif "on Linkedin" in detail:
                            company_dict["num_employees_on_linkedin"] = detail
                        else:
                            company_dict["industry"] = detail

            job.company = Company(**company_dict)

        # Workplace type, Employment type, Seniority level
        if (
            insights_container := soup.find(
                "li",
                attrs={"class": "job-details-jobs-unified-top-card__job-insight--highlight"},
            )
        ) and (insights := insights_container.find("span")):
            for elm in insights:
                if stripped_text := elm.text.strip():
                    if "workplace type is" in stripped_text:
                        job.workplace_type = stripped_text.split()[-1].strip(".")
                        job.remote = True if job.workplace_type == "Remote" else False
                    elif "job type is" in stripped_text:
                        job.employment_type = stripped_text.split()[-1].strip(".")
                    elif "/" not in stripped_text:
                        job.seniority_level = stripped_text

        # Hiring manager details
        if hirer_card := soup.find("div", attrs={"class": "hirer-card__hirer-information"}):
            job.hiring_manager = HiringManager(
                name=hirer_card.find("span", attrs={"class": "jobs-poster__name"}).text.strip(),
                title=hirer_card.find(
                    "div",
                    attrs={"class": lambda class_name: class_name in ("hirer-card__hirer-job-title", "linked-area")},
                ).text.strip(),
                linkedin_url=hirer_card.find("a", attrs={"href": True}).attrs["href"],
                company_name=job.company.name,
            )

        # Job description
        if description_container := soup.find("div", attrs={"id": "job-details"}):
            job.description = description_container.text.replace("About the job", "").replace("About Us", "").strip()

        # Salary and benefits details
        if salary_container := soup.find("div", attrs={"id": "SALARY"}):
            if (
                (salary_divs := salary_container.find_all("div", attrs={"class": "mt4"}))
                and len(salary_divs) > 1
                and (salary_p := salary_divs[1].find("p"))
            ):
                pay_range = [s.replace("$", "").replace(",", "") for s in salary_p.text.strip().split() if "/" in s]
                min_pay = pay_range[0]
                if len(pay_range) > 1:
                    max_pay = pay_range[1]
                else:
                    max_pay = min_pay

                if min_pay.endswith("/hr"):
                    job.min_hourly = float(min_pay[:-3])
                    job.max_hourly = float(max_pay[:-3])
                    job.min_salary = job.min_hourly * 40 * 50
                    job.max_salary = job.max_hourly * 40 * 50
                    job.pay_type = "hourly"
                elif min_pay.endswith("/yr"):
                    job.min_salary = float(min_pay[:-3])
                    job.max_salary = float(max_pay[:-3])
                    job.min_hourly = job.min_salary / (40 * 50)
                    job.max_hourly = job.max_salary / (40 * 50)
                    job.pay_type = "salary"

            if benefits_items := salary_container.find_all("li", attrs={"class": "featured-benefits__benefit"}):
                job.benefits = [elm.text.strip() for elm in benefits_items]

        # Job skills
        if skills_items := soup.find_all("a", attrs={"class": "job-details-how-you-match__skills-item-subtitle"}):
            job.skills = []
            for elm in skills_items:
                for skill in elm.text.strip().split(","):
                    skill = skill.strip()
                    if skill.startswith("and "):
                        skill = skill[4:]
                    job.skills.append(skill)

        # Easy Apply (Determines if job can be applied to directly from LinkedIn)
        if apply_button := soup.find("div", attrs={"class": "jobs-apply-button--top-card"}):
            job.easy_apply = "Easy Apply" in apply_button.text or "Continue" in apply_button.text

        # Closed job application status
        elif feedback_message := soup.find("span", attrs={"class": "artdeco-inline-feedback__message"}):
            if "No longer accepting applications" in feedback_message.text:
                job.status = "closed"

        # Post submission application status (applied, viewed, downloaded, etc.)
        if post_apply_content := soup.find("div", attrs={"class": "post-apply-timeline__content"}):
            for post_appy_entity in post_apply_content.find_all("li", attrs={"class": "post-apply-timeline__entity"})[
                ::-1
            ]:
                activity = post_appy_entity.find("span", attrs={"class": "full-width"}).text.strip()
                time = post_appy_entity.find("span", attrs={"class": "post-apply-timeline__entity-time"}).text.strip()
                if activity == "Resume downloaded":
                    job.status = "downloaded"
                    break
                if activity == "Application viewed":
                    job.status = "viewed"
                    break
                elif activity == "Application submitted" and job.status not in (
                    "applied",
                    "downloaded",
                    "viewed",
                ):
                    job.status = "applied"
                print(activity, time)

        # Initially set status to 'scraped' if not already set
        job.date_scraped = datetime.now()
        if not job.status:
            job.status = "scraped"

        # Update the job in the db with the new details
        self.job_app_db.update_model(job)
        return job

    def apply_to_job(self, job: Job) -> Job:
        """Applies to a job on LinkedIn using the provided Job object."""
        # Navigate to the job page and update the job details then wait for the apply button to load
        job = self.update_job(job)
        self.scraper.wait_for_visibility_of_element_located_by_class_name("jobs-apply-button--top-card").click()

        # Fill out the job application form until complete or an error occurs
        status = "incomplete"
        while (soup := self.scraper.soup) and not soup.find("button", attrs={"aria-label": "Submit application"}):
            try:
                # Loop through input element and Question pairs
                for input_elm, question in self.get_questions():
                    needs_input = not question.answer

                    # Get the answer from the DB if it exists
                    if (
                        saved_question := self.job_app_db.get_model(Question, question.question)
                    ) and saved_question.answer:
                        question.answer = saved_question.answer
                    else:
                        # Or add it to the DB if it doesn't exist yet and ask the AI or user for an answer
                        self.job_app_db.insert_model(question)

                    if not question.answer:
                        # Ask the AI or user for an answer if not prefilled and update the DB
                        question = self.answer_job_question(question)
                        self.job_app_db.update_model(question)

                        # Exit if the question is still unanswered after asking the AI and user
                        if not question.answer:
                            status = "needs answer"
                            break

                    if needs_input:
                        # Input the answer when not prefilled
                        if isinstance(input_elm, dict):
                            # Get the input element corresponding to the answer choice if there are multiple inputs
                            input_elm = input_elm[question.answer]

                        # Scroll to the input element and click it to focus
                        self.scraper.scroll_to(input_elm).click()

                        try:
                            # Attempt to send the answer to the input element and tab to the next input
                            input_elm.send_keys(question.answer)
                            input_elm.send_keys(Keys.TAB)
                        except Exception as e:
                            print(f"Failed to send keys to element. Ignoring error: {e}")

                # Upload cover letter if needed
                if upload_elms := soup.find_all("label", attrs={"class": "jobs-document-upload__upload-button"}):
                    for upload_elm in upload_elms:
                        if "Upload cover letter" in upload_elm.text:
                            if self.cover_letter_action == "skip":
                                upload_success = False
                            elif self.cover_letter_action == "default":
                                upload_success = self.upload_cover_letter(self.default_cover_letter_path)
                            elif self.cover_letter_action == "generate":
                                cover_letter_path = self.generate_cover_letter(job)
                                upload_success = self.upload_cover_letter(cover_letter_path)

                            # Exit if a cover letter is needed but not uploaded
                            if not upload_success:
                                status = "needs cover letter"
                                print("Failed to upload cover letter. Skipping.")
                                break

                # Exit the application loop if input is needed from the user to continue
                if status in ("needs answer", "needs cover letter"):
                    break

                # Click the next button to continue to the next step or review the application
                if soup.find("button", attrs={"aria-label": "Continue to next step"}):
                    self.click_button_with_aria_label("Continue to next step")

                elif soup.find("button", attrs={"aria-label": "Review your application"}):
                    self.click_button_with_aria_label("Review your application")

            except Exception as e:
                print(f"Failed to answer questions. Error: {e}")
                status = "error"
                break

        # An application is complete if the submit button is found
        if soup.find("button", attrs={"aria-label": "Submit application"}):
            status = "complete"

        if status != "complete":
            print(f"Failed to apply to job {job.title} at {job.company.name} in {job.location}. Status: {status}")
            job.status = status
            self.job_app_db.update_model(job)
            # Close and save the application for later then return the job if the application is incomplete
            self.click_button_with_aria_label("Dismiss")
            self.scraper.find_element_by_css_selector("button[data-control-name='save_application_btn']").click()
            return job

        try:
            # Attempt to unfollow the company after applying
            self.scraper.find_element_by_css_selector("label[for='follow-company-checkbox']").click()
        except Exception as e:
            print(f"Failed to unfollow company. Ignoring. Error: {e}")

        # Submit the application, update the job in the Db, and return the job
        self.click_button_with_aria_label("Submit application")
        job.status = "applied"
        job.date_applied = datetime.now()
        self.job_app_db.update_model(job)
        print(f"Applied to job {job.title} at {job.company.name} in {job.location}")
        return job

    def upload_cover_letter(self, cover_letter_path: Union[str, Path]) -> bool:
        """Uploads a cover letter to the LinkedIn job application form."""
        cover_letter_path = cover_letter_path if isinstance(cover_letter_path, str) else str(cover_letter_path)
        for input_elm in self.scraper.find_elements_by_css_selector("input[name='file']"):
            if "cover-letter" in input_elm.get_attribute("id"):
                input_elm.send_keys(cover_letter_path)
                return True
        return False

    def get_questions(
        self,
    ) -> Iterator[Tuple[Union[WebElement, Dict[str, WebElement]], Question]]:
        """Yields Question objects and the corresponding input elements on the LinkedIn job application form."""
        question_count = 0
        for form_elm in self.scraper.find_elements_by_class_name("jobs-easy-apply-form-section__grouping"):
            # Simple text input
            for container_elm, input_elm in zip(
                form_elm.find_elements("class name", "artdeco-text-input--container"),
                form_elm.find_elements("class name", "artdeco-text-input--input"),
            ):
                question_text = container_elm.text
                current_val = input_elm.get_attribute("value")
                question_count += 1
                yield input_elm, Question(question=question_text, answer=current_val, choices=None)

            # TODO Test with https://www.linkedin.com/jobs/view/3864508460/
            # Textarea multi-line input
            for textarea in form_elm.find_elements("tag name", "textarea"):
                question_text = textarea.get_attribute("aria-label")
                current_val = textarea.get_attribute("value")
                question_count += 1
                yield textarea, Question(question=question_text, answer=current_val, choices=None)

            # Dropdown selection
            for select_elm in form_elm.find_elements("tag name", "select"):
                question_text = select_elm.accessible_name
                choices = [elm.accessible_name for elm in select_elm.find_elements("tag name", "option")[1:]]
                current_val = value if (value := select_elm.get_attribute("value")) != "Select an option" else None
                if question_text != "Select Language":
                    question_count += 1
                    yield select_elm, Question(question=question_text, answer=current_val, choices=choices)

            # Form input with choices (radio, checkbox, etc.)
            for form_label in form_elm.find_elements("class name", "fb-dash-form-element__label"):
                question_text = form_label.find_element("tag name", "span").text
                # Label refers to input element by id and input is interactable
                if input_id := form_label.get_attribute("for"):
                    input_elm = form_elm.find_element("id", input_id)
                    current_val = input_elm.get_attribute("value")
                    question_count += 1
                    yield input_elm, Question(question=question_text, answer=current_val, choices=None)

                else:
                    # Each choice is a separate label/input element pair, but the input is not interactable, the label is
                    choices = []
                    input_elms = {}
                    for select_elm in form_elm.find_elements("class name", "fb-text-selectable__option"):
                        choice = select_elm.text
                        choices.append(choice)
                        input_elms[choice] = select_elm.find_element("tag name", "label")

                    question_count += 1
                    yield input_elms, Question(question=question_text, answer=None, choices=choices)

        if question_count == 0:
            print("Failed to find input element for question. Skipping")

        return question_count

    def _try_func_on_jobs(
        self,
        jobs: Iterable[Job],
        func: Callable[[Job], Job],
        new_tab=False,
        close_tab_after=False,
    ) -> Iterator[Job]:
        """Tries to preform a function to each job in the provided iterable and yields the job if successful."""
        initial_tab = self.scraper.current_tab
        for job in jobs:
            print(f"Trying {func} on {job.id}: {job.title} at {job.company.name} in {job.location}")
            try:
                if new_tab:
                    self.scraper.new_tab()
                    self.scraper.switch_to_tab(index=-1)
                yield func(job)
            except Exception as e:
                print(f"Failed {job.id}: {job.title} at {job.company.name} in {job.location}. Error: {e}")

            if new_tab and close_tab_after:
                try:
                    self.scraper.close()
                except Exception as e:
                    print(f"Failed to close tab. Error: {e}")

                try:
                    self.scraper.switch_to_tab(window_handle=initial_tab)
                except Exception as e:
                    print(f"Failed to switch back to initial tab. Error: {e}")

    def apply_to_jobs(self, jobs: Iterable[Job]) -> Iterator[Job]:
        """Applies to each job in the provided iterable"""
        return self._try_func_on_jobs(jobs, self.apply_to_job)

    def update_jobs(self, jobs: Iterable[Job]) -> Iterator[Job]:
        """Updates/re-scrapes each job in the provided iterable"""
        return self._try_func_on_jobs(jobs, self.update_job)

    def open_jobs(self, jobs: Iterable[Job]) -> Iterator[Job]:
        """Opens a new tab with the LinkedIn job page for each job in the provided iterable"""
        return self._try_func_on_jobs(jobs, self.goto_job, new_tab=True, close_tab_after=False)

    def answer_job_question(self, question: Question) -> Question:
        """Asks the AI or user to answer a job application question."""
        # Otherwise have the AI answer the question
        question, *_ = self.ai.answer_job_questions(question)
        return question

    def generate_cover_letter(self, job: Job) -> Path:
        """Generates a cover letter for the provided job using the AI."""
        cover_letter_paths = self.ai.write_job_cover_letters(job)
        return cover_letter_paths[job]
