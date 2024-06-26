# linkedin-ai

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![openai](https://img.shields.io/badge/OpenAI-412991.svg?style=for-the-badge&logo=OpenAI&logoColor=white)
![selenium](https://img.shields.io/badge/Selenium-43B02A.svg?style=for-the-badge&logo=Selenium&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-41CD52.svg?style=for-the-badge&logo=Qt&logoColor=white)
![pydantic](https://img.shields.io/badge/Pydantic-E92063.svg?style=for-the-badge&logo=Pydantic&logoColor=white)

[![PyPI version](https://badge.fury.io/py/linkedin-ai.svg)](https://badge.fury.io/py/linkedin-ai)
![GitHub issues](https://img.shields.io/github/issues/LucasFaudman/linkedin-ai)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

Automate **searching for jobs** and **submitting applications** on LinkedIn using OpenAI.

- [Why use LinkedIn AI?](#why-use-linkedin-ai)
- [Features](#features)
- [Installation](#installation)
  - [PyPi Install Command](#pypi-install-command)
  - [From Source Install Commands](#from-source-install-commands)
  - [Chromedriver Download (REQUIRED)](#downloading-chromedriver)
  - [OpenAI API Key Setup (REQUIRED)](#openai-api-key-setup)
- [Usage: (How to run the LinkedIn Automator GUI App)](#usage-how-to-run-the-linkedin-automator-gui-app)
- [Searching for Jobs](#searching-for-jobs)
    - [Search Filters and Job Collections](#search-filters-and-job-collections)
    - [Removing Jobs From Search Results](#removing-jobs-from-search-results)
    - [Finding Easy-Apply Jobs](#finding-easy-apply-jobs)
- [Submitting Job Applications](#submitting-job-applications)
    - [Providing your Resume as Context for your AI](#providing-your-resume-as-context-for-your-ai)
    - [Training your AI to Answer Questions Like You](#training-your-ai-to-answer-questions-like-you)
    - [Full Automation](#full-automation)
- [Generating Custom Cover Letters](#generating-custom-cover-letters)
    - [Cover Letter Options](#cover-letter-options)
    - [Providing Cover Letter Examples](#providing-cover-letter-examples)
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
---



## Searching For Jobs
LinkedIn AI supports **all** LinkedIn Search Filters.

### Search Filters and Job Collections

### Removing Jobs From Search Results

### Finding Easy-Apply Jobs

---


## Submitting Job Applications

### Providing your Resume as Context for your AI

### Training your AI to Answer Questions Like You

### Full Automation

---

## Generating Custom Cover Letters

### Cover Letter Options

### Providing Cover Letter Examples


---

## Viewing and Managing your Saved Jobs DB
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
