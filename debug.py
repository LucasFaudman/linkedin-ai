from code import interact
from json import load
from src.linkedin_ai import liautomator, app, models

with open("linkedin-ai-config.json") as f:
    config = load(f)
    config.pop("li_auto_login", None)

li_auto = liautomator.LinkedInAutomator(**config)
li_auto.init_dbs()
li_auto.init_scraper()
li_auto.login()

jobs = li_auto.job_app_db.get_models(models.Job, *input("Input test job ids: ").strip().split())
interact(local=locals())
