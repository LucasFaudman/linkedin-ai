# LinkedIn AI
<!-- > **NOTE:** DOCS CURRENTLY A WORK IN PROGRESS. MORE DETAILED INSTRUCTIONS COMING SOON. -->

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![openai](https://img.shields.io/badge/OpenAI-412991.svg?style=for-the-badge&logo=OpenAI&logoColor=white)
![selenium](https://img.shields.io/badge/Selenium-43B02A.svg?style=for-the-badge&logo=Selenium&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-41CD52.svg?style=for-the-badge&logo=Qt&logoColor=white)
![pydantic](https://img.shields.io/badge/Pydantic-E92063.svg?style=for-the-badge&logo=Pydantic&logoColor=white)

[![PyPI version](https://badge.fury.io/py/linkedin-ai.svg)](https://badge.fury.io/py/linkedin-ai)
![GitHub issues](https://img.shields.io/github/issues/LucasFaudman/linkedin-ai)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

Automate **searching for jobs** and **submitting applications** on LinkedIn using OpenAI.

![demo-teaser](https://github.com/LucasFaudman/linkedin-ai/assets/52257695/76eedba2-70bd-46d6-892f-c9057e3dcb5a)

## Index
- [Why use LinkedIn AI?](#why-use-linkedin-ai)
<!-- - [Features](#features) -->
- [Installation](#installation)
  - [PyPi Install Command](#pypi-install-command)
  - [From Source Install Commands](#from-source-install-commands)
  - [Chromedriver Download (REQUIRED)](#chromedriver-download)
  - [OpenAI API Key Setup (REQUIRED)](#openai-api-key-setup)
- [Usage (How to run the LinkedIn AI GUI App)](#usage-how-to-run-the-linkedin-ai-gui-app)
- [Searching for Jobs](#searching-for-jobs)
    - [Search Filters and Job Collections](#search-filters-and-job-collections)
    - [Removing Jobs From Search Results](#removing-jobs-from-search-results)
    - [Finding 'Easy Apply' Jobs (Application can be Submitted on LinkedIn)](#finding-easy-apply-jobs)
- [Submitting Job Applications](#submitting-job-applications)
    - [Providing your Resume as Context for your AI](#providing-your-resume-as-context-for-your-ai)
    - [Training your AI to Answer Questions Like You](#training-your-ai-to-answer-questions-like-you)
    - [AI Automation Options](#ai-automation-options)
- [Generating Custom Cover Letters](#generating-custom-cover-letters)
    - [Cover Letter Options](#cover-letter-options)
- [Viewing and Managing your Saved Jobs DB](#viewing-and-managing-your-saved-jobs-db)
    - [Filtering Saved Jobs](#filtering-saved-jobs)
    - [Opening Saved Jobs](#opening-saved-jobs)
    - [Updating Saved Jobs](#updating-saved-jobs)
- [Contributing](#contributing)
- [License](#license)

---

## Why use LinkedIn AI?

### Keep Up with the AI-Driven Job Market
With over [88% of companies](https://artsmart.ai/blog/how-many-companies-use-ai-in-hiring/) using AI in their recruitment processes in 2024 and applicants requiring [hundreds of applications per offer](https://www.lifeshack.com/resources/job-search/how-many-applications-does-it-take-to-find-a-job-in-2024/), leveraging AI for your job search has become essential to keep up.

> Your application is most likely being read by an AI tool—so why not have it written by one too?

### Automate Finding Jobs
> LinkedIn AI **streamlines your job search process**, allowing you to **find relevant job postings efficiently**.

It leverages LinkedIn's **advanced search filters** and [`SouperScraper`]() to search through the hundreds of applications and **pinpoint opportunities that match your criteria, saving you time and effort**.

### Automate Filling Out and Submitting Job Applications
> LinkedIn AI **automates the repetitive and time-consuming task of filling out job applications**.

Using your resume and previously provided answers stored in your Jobs DB, the **AI can answer application questions accurately**, making the submission process faster and more consistent.

### Automate Application Tailoring
> LinkedIn AI **automates cover letter writing and editing** to **tailor your application to address the specific requirements of each job**.

Using your resume, previous answers, and example cover letters you provide the **AI can generate a custom cover letter for each job based on the posting's details** and, if available, the hiring manager's name.

### Easily View and Manage the Jobs You've Saved
LinkedIn AI provides an intuitive interface to **view and manage your saved jobs**. You can **filter**, **update**, and **organize** your job applications, ensuring you stay on top of your job search and never miss an opportunity.

### Contacts and Messaging Coming Soon
Additionally, LinkedIn AI collects Hiring Manager information with each job listing. Future updates will include features for **custom message sending** and **automatic connection requests**, enhancing your networking capabilities directly through the application.

<!-- ## Features -->

---

## Installation
> LinkedIn AI can be installed from PyPi or from source.

### PyPi Install Command
```bash
pip3 install linkedin-ai
```

### From Source Install Commands
```bash
git clone https://github.com/LucasFaudman/linkedin-ai.git
cd linkedin-ai
python3 -m venv .venv
source .venv/bin/activate
pip3 install -e .
```

> **IMPORTANT:** After installing `linkedin-ai`, you will still need to **download the correct Chromedriver** AND **setup your OpenAI API Key**.

### Chromedriver Download
Download the appropriate [ChromeDriver](https://sites.google.com/a/chromium.org/chromedriver/downloads) for your Chrome version using [getchromedriver.py](https://github.com/LucasFaudman/souper-scraper/blob/main/src/souperscraper/getchromedriver.py) (command below) or manually from the [ChromeDriver website](https://sites.google.com/a/chromium.org/chromedriver/downloads).
> To find your Chrome version, go to [`chrome://settings/help`](chrome://settings/help) in your browser.
```bash
getchromedriver
```

### OpenAI API Key Setup
Instructions to setup your OpenAI API key can be found [at this link](https://platform.openai.com/docs/quickstart/step-2-set-up-your-api-key)


> Once you have the **path to your chromedriver** and **OpenAI API Key** you are ready to use LinkedIn AI.

---



## Usage: (How to run the LinkedIn AI GUI App)
Run the command below to open the LinkedIn AI App:
```bash
linkedin-ai
```
> This will use the default config path `./linkedin-ai-config.json`

To specify a custom config path use the `--config/-c` argument:
```bash
linkedin-ai --config /path/to/custom/config.json
```
> Startup command, manual login (auto login can be enable in settings), and post-login initialization:
![demo-run-login](https://github.com/LucasFaudman/linkedin-ai/assets/52257695/c7c98052-3fdf-407d-8903-472ea6e1542e)

---

## Searching For Jobs
> LinkedIn AI supports all LinkedIn **Search Filters** and **Job Collections**.
![demo-search-only](https://github.com/LucasFaudman/linkedin-ai/assets/52257695/8194065f-5a65-4878-9f99-a32df918289d)

### Search Filters and Job Collections


> **NOTE:** Available filters may differ based on the Search Term. Click the `Update Filter Options` button to refresh the filters in the UI.

### Removing Jobs From Search Results
Any jobs you are not interested in can be removed by selecting them and clicking `Remove Selected Items`.
> **NOTE:** This will prevent these jobs from being written to your Jobs DB.

### Finding 'Easy Apply' Jobs (Application can be Submitted on LinkedIn)
The first filter `Easy Apply` determines if the job application can be completed natively through LinkedIn.
> **IMPORTANT:** All jobs can be searched for, stored in the Jobs DB, scraped, opened, etc, but currently **ONLY 'Easy Apply' applications can be submitted by the AI.**

---


## Submitting Job Applications
> LinkedIn AI uses your **Resume** and your **answers to previous job applications questions stored in the Jobs DB** as the context to answer future questions about related topics.


![demo-apply-answer-needed](https://github.com/LucasFaudman/linkedin-ai/assets/52257695/c6a025d7-fd05-4e5b-b7d0-28a4ca33224d)


### Providing your Resume as Context for your AI
In the `Settings` tab you can select the path you to your **Resume as a plaintext `.txt` file**.

> **IMPORTANT:** Anything in this file will be considered by the AI on *every* question while questions in the DB will only be considered when *relevant* to the current question.

If you have a PDF [convert it](https://www.google.com/search?q=.pdf+to+.txt) or copy it with `CTRL+A`, `CTRL+C`, `echo 'CTRL+V' > resume.txt`. (Might add auto `.pdf`->`.txt` with PikePDF or similar in future if it’s requested.)


### Training your AI to Answer Questions Like You
At first, the AI will frequently respond with `ANSWER UNKOWN` since it does not have enough context in the DB yet to answer tough questions about things not in your resume.

When this happens you will be prompted to provide the answer, and next time the AI sees a similar question, **your related answers will be used to determine the answer**.

Any questions you have already answered in previous job applications on LinkedIn will automatically be added to your DB for future use.


> **IMPORTANT:** Begin by first doing applications with `Ask for Answer When Needed` and `Verify AI Provided Answers` **both checked**. Once you are satisfied with the accuracy of the AI answers, then you can allow it to run fully autonomously by unchecking `Verify AI Provided Answers`.


### AI Automation Options
> Determine the **level of autonomy** given to LinkedIn AI and **when it should stop to ask you to *approve*, *edit*, or *enter*** an answer.

| Automation Option | Checked | Unchecked |
| --- | --- | --- |
| `Ask for Answer When Needed` | **Ask you for the answer** when the AI is selects `ANSWER UNKNOWN`. **Save the answer you provided**, question, and choices, in the DB for future context. | Sets job status to `needs answer`, save progress on LinkedIn, and continue with next application. **Answer is NOT saved in the DB**. |
| `Verify AI Provided Answers` | **Always ask you to verify/edit AI answers before submitting**, even when the AI selects an answer it thinks is correct. **Keep this enabled until you are satisfied with AI answers.** | **Use the AI provided answers** to fill out the application, ***without*** asking you each time. **Answers are saved to the DB** to avoid wasting tokens on repeat questions. |

---

| `Ask for Answer When Needed` | `Verify AI Provided Answers` | AI Selects an Answer | AI Selects `ANSWER UNKNOWN` | Action |
| --- | --- | --- | --- | --- |
| Checked | Checked | **Ask you before submitting** to ***approve or edit*** the answer. | **Ask you before submitting** to ***enter or select*** the answer. |
| Unchecked | Checked | **Ask you before submitting** to ***approve or edit*** the answer. | **Skip question**, set job status to `needs answer`, **save progress** for later, and ***begin next application***. |
| Checked | Unchecked | **Submit the answer ***without*** asking**. | **Ask you before submitting** to ***enter or select*** the answer. |
| Unchecked | Unchecked | **Submit the answer ***without*** asking** | **Skip question**, set job status to `needs answer`, **save progress** for later, and ***begin next application***. |







## Generating Custom Cover Letters
> Feature is currently enabled and working, but UI improvements coming soon. Docs will be finished once UI is stable.

The `Default Cover Letter Path` setting is the file that will either be used as:
- A generic cover letter to upload to all jobs that request a cover letter.
- An example cover letter for the AI to use to understand your writing style.

### Cover Letter Options
> Determines how LinkedIn AI will handle jobs that ask for cover letters.

| Cover Letter Option | When an Job Asks for a Cover Letter |
| --- | --- |
| `Skip Cover Letters` | Save application and sets job status to `needs cover letter` |
| `Use Default Cover Letter for all jobs` | Upload the file at `Default Cover Letter Path` |
| `Generate Custom Cover Letter for each job` | AI will use `Default Cover Letter Path` as an example of how you write, then write a custom cover letter based on the job description, hiring manager's name, your Resume `.txt` file, and your answers in the Db |

> **NOTE:** When using `Generate Custom Cover Letter for each job` the file at `Default Cover Letter Path` can include any number cover letter examples as long as it is clear to the AI where each one begins and ends.

---

## Viewing and Managing your Saved Jobs DB
> Feature is currently enabled and working, but UI improvements coming soon. Docs will be finished once UI is stable.
### Filtering Saved Jobs
### Opening Saved Jobs
### Updating Saved Jobs

---

## Contributing

Contributions welcome! Whether you're interested in fixing bugs, adding new features, improving documentation, or sharing ideas, any input is valuable.

### How to Contribute

1. **Fork the Repository:** Start by forking the repository on GitHub. This will create a copy of the project in your own GitHub account.

2. **Clone the Repository:** Clone the forked repository to your local machine.

    ```bash
    git clone https://github.com/LucasFaudman/linkedin-ai.git
    cd linkedin-ai
    ```

3. **Create a Branch:** Create a new branch for your changes.

    ```bash
    git checkout -b my-feature-branch
    ```

4. **Make Changes:** Make your changes in the code, documentation, or both.

5. **Commit Changes:** Commit your changes with a descriptive commit message.

    ```bash
    git add .
    git commit -m "Description of the changes"
    ```

6. **Push Changes:** Push your changes to your forked repository.

    ```bash
    git push origin my-feature-branch
    ```

7. **Create a Pull Request:** Go to the original repository and create a pull request from your branch. Provide a detailed description of your changes and any relevant information.

### Issues

If you encounter any bugs, have suggestions, or need help, please open an issue on GitHub. Make sure to provide as much detail as possible, including steps to reproduce the issue, error messages, and screenshots if applicable.


---


## License
> See [LICENSE](https://github.com/LucasFaudman/linkedin-ai/blob/main/LICENSE) for details.
