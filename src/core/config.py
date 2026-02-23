import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.environ.get("DB_PATH", "courses.db")
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = "".join(DATABASE_URL.split())

ALLOWED_EXTENSIONS = {"pdf"}

LOCATION_CLEANUP = {
    "Harrogate, UK": "Harrogate",
    "Oxford Botanical Gardens": "Oxford",
}
