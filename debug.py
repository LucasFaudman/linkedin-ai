from code import interact
from json import load
from src.linkedin_ai import liautomator, app, models

if __name__ == "__main__":
    if (choice := input("Debug app (a)? linkedin-ai (l)? quit (q)?").strip().lower()).startswith("a"):
        app.main()
    elif choice.startswith("l"):
        with open("linkedin-ai-config.json") as f:
            config = load(f)
            config.pop("li_auto_login", None)
        li_auto = liautomator.LinkedInAutomator(**config)
        li_auto.init_dbs()
        li_auto.init_scraper()
        li_auto.login()
        interact(local=locals())
    else:
        exit()
