import os
from dotenv import load_dotenv

load_dotenv(override=False)

DB_PATH = os.environ.get("DB_PATH", "courses.db")
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = "".join(DATABASE_URL.split())

ALLOWED_EXTENSIONS = {"pdf"}

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()
DEV_BYPASS_AUTH = (
    ENVIRONMENT == "development"
    and os.environ.get("DEV_BYPASS_AUTH", "true").lower() == "true"
)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

SUPABASE_ANON_KEY = SUPABASE_PUBLISHABLE_KEY or os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = SUPABASE_SECRET_KEY or os.environ.get("SUPABASE_SERVICE_KEY")

LOCATION_CLEANUP = {
    "Harrogate, UK": "Harrogate",
    "Oxford Botanical Gardens": "Oxford",
}
