# LinkedIn AI
> NOTE DOCS CURRENTLY WORK IN PROGRESS. MORE DETAILED INSTRUCTIONS COMING SOON.

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
- [Features](#features)
- [Installation](#installation)
  - [PyPi Install Command](#pypi-install-command)
  - [From Source Install Commands](#from-source-install-commands)
  - [Chromedriver Download (REQUIRED)](#chromedriver-download)
  - [OpenAI API Key Setup (REQUIRED)](#openai-api-key-setup)
- [Usage: (How to run the LinkedIn Automator GUI App)](#usage-how-to-run-the-linkedin-automator-gui-app)
- [Searching for Jobs](#searching-for-jobs)
    - [Search Filters and Job Collections](#search-filters-and-job-collections)
    - [Removing Jobs From Search Results](#removing-jobs-from-search-results)
    - [Finding Easy-Apply Jobs](#finding-easy-apply-jobs)
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

### Automate Finding Jobs.

### Automate Filling Out and Submitting Job Applications

### Easily View and Manage the Jobs You've Saved

## Features

---

## Installation
> Linkedin AI can be installed from PyPi or from source.

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

> **IMPORTANT**: After installing linkedin-ai, you will still need to **download the correct Chromedriver** AND **setup your OpenAI API Key**.

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



## Usage: (How to run the LinkedIn Automator GUI App)
Run the command below to open the LinkedIn Automator App:
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


> NOTE: Available filters may differ based on the Search Term. Click the `Update Filter Options` button to refresh the filters in the UI.

### Removing Jobs From Search Results
> After searching, any jobs you are not interested in can be removed by selecting them and clicking `Remove Selected Items`. This will prevent these jobs from being written to your Jobs DB.

### Finding Easy-Apply Jobs
> IMPORTANT: The filter Easy-Apply determines if the job application can be completed natively through LinkedIn.
> All jobs can be searched for, stored in the Jobs DB, scraped, opened, etc, but currently **ONLY Easy-Apply applications can be submitted by the AI.**

---


## Submitting Job Applications
> LinkedIn AI uses your **Resume** and your **answers to previous job application stored in the Jobs DB** questions as the context to answer future questions. 

 
![demo-apply-answer-needed](https://github.com/LucasFaudman/linkedin-ai/assets/52257695/c6a025d7-fd05-4e5b-b7d0-28a4ca33224d)







### Providing your Resume as Context for your AI
> Under the `Settings` tab you can select the path you to **your Resume as a plaintext `.txt` file**. 
> **Anything in this file will be considered by the AI on *every* question.** unlink previous questions which will only be considered if relevant.
> It must be plaintext to use as few tokens as possible, which significantly **reduces AI API costs** and **improves accuracy** by leaving more of the context window available to consider previous questions relevant to the question being answered.

### Training your AI to Answer Questions Like You
> At first, the AI will frequently respond with `ANSWER UNKOWN` since it will not many answered saved in the Db yet. When this happens you will be prompted to provide the answer, and next time the AI sees a similar question, your answer will be used to determine the answer.
> Any questions you have already answered in previous job applications on LinkedIn will automatically be added to your DB for future use.
> IMPORTANT: Begin by first doing applications with both `Ask for Answer When Needed` and `Verify AI Provided Answers` enabled. Once you are satisfied with the accuracy of the AI answers, then you can allow it to run fully autonomously.


### AI Automation Options
| Automation Option | Checked | Unchecked |
| --- | --- | --- |
| `Ask for Answer When Needed` | Ask you for the answer when the AI is unsure. Store question, answer and choices, for future context. | Set job status to `needs answer`, save progress on LinkedIn and continue with next application. |  
| `Verify AI Provided Answers` | Always verify AI answers before submitting. **Keep enabled until you are satisfied with AI answers.** | Set job status to `needs answer`, save progress on LinkedIn and continue with next application. | 

> IMPORTANT: If both are unchecked, LinkedIn AI will skip each application unless every question has an answer are already saved in your DB. To go back and finish them later you can filter for jobs with status `needs answer` in the `View Job Database` tab.

---

## Generating Custom Cover Letters
> Feature is currently available and working, but UI improvements coming soon. Docs will be finished once UI is stable.

The `Default Cover Letter Path` setting is the file that will either be used as:
- A generic cover letter to upload to all jobs that request a cover letter.
- An example cover letter for the AI to use to understand your writing style.

### Cover Letter Options
> Determines how LinkedIn AI will handle jobs that ask for cover letters.

| Cover Letter Option | When an Job Asks for a Cover Letter | 
| --- | --- | 
| `Skip Cover Letters` | Save application and sets job status to `needs cover letter` |
| `Use Default Cover Letter for all jobs` | Upload the file at `Default Cover Letter Path` |
| `Generate Custom Cover Letter for each job` | AI will use `Default Cover Letter Path` as an example of how you write, then write a custom cover letter based on the job description, hiring manager's name, your Resume `.txt` file, and your answers in the Db` | 

> NOTE: When using `Generate Custom Cover Letter for each job` the file at `Default Cover Letter Path` can include any number cover letter examples as long as it is clear to the AI where each one begins and ends. 

---

## Viewing and Managing your Saved Jobs DB
> Feature is currently available and working, but UI improvements coming soon. Docs will be finished once UI is stable.
### Filtering Saved Jobs
### Opening Saved Jobs
### Updating Saved Jobs

---

## Contributing

Contributions welcome! Whether you're interested in fixing bugs, adding new features, improving documentation, or sharing ideas, any input is valuable.

### How to Contribute

1. **Fork the Repository**: Start by forking the repository on GitHub. This will create a copy of the project in your own GitHub account.

2. **Clone the Repository**: Clone the forked repository to your local machine.

    ```bash
    git clone https://github.com/LucasFaudman/linkedin-ai.git
    cd linkedin-ai
    ```

3. **Create a Branch**: Create a new branch for your changes.

    ```bash
    git checkout -b my-feature-branch
    ```

4. **Make Changes**: Make your changes in the code, documentation, or both.

5. **Commit Changes**: Commit your changes with a descriptive commit message.

    ```bash
    git add .
    git commit -m "Description of the changes"
    ```

6. **Push Changes**: Push your changes to your forked repository.

    ```bash
    git push origin my-feature-branch
    ```

7. **Create a Pull Request**: Go to the original repository and create a pull request from your branch. Provide a detailed description of your changes and any relevant information.

### Issues

If you encounter any bugs, have suggestions, or need help, please open an issue on GitHub. Make sure to provide as much detail as possible, including steps to reproduce the issue, error messages, and screenshots if applicable.


---


## License
> See [LICENSE](https://github.com/LucasFaudman/linkedin-ai/blob/main/LICENSE) for details.
