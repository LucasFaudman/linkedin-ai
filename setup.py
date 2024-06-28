from setuptools import setup, find_packages
import setuptools_scm  # noqa

with open("README.md", mode="r", encoding="utf-8") as f:
    README = f.read()

setup(
    name="linkedin-ai",
    version="0.6.5",
    use_scm_version=True,
    setup_requires=["setuptools_scm>=8", "wheel"],
    description="Automate searching for jobs and submitting applications on LinkedIn using OpenAI",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Lucas Faudman",
    author_email="lucasfaudman@gmail.com",
    url="https://github.com/LucasFaudman/linkedin-ai.git",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[],
    python_requires=">=3.7",
    license="LICENSE.txt",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords=[
        "linkedin",
        "openai",
        "automation",
        "job",
        "applications",
        "ai",
        "linkedin-ai",
        "linkedin scraper",
        "linkedin job applications",
        "linkedin automation",
        "selenium",
        "beautifulsoup",
        "bs4",
        "PyQt5",
        "gui",
        "pydantic",
        "sqldantic",
    ],
    project_urls={
        "Homepage": "https://github.com/LucasFaudman/linkedin-ai.git",
        "Repository": "https://github.com/LucasFaudman/linkedin-ai.git",
    },
    entry_points={
        "console_scripts": [
            "linkedin-ai = linkedin_ai.app:main",
        ],
    },
)
