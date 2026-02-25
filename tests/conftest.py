import os

test_db_path = "/tmp/test_dandori.db"
os.environ["DB_PATH"] = test_db_path
os.environ["DATABASE_URL"] = ""
os.environ["VECTOR_STORE_PROVIDER"] = "chroma"
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENROUTER_API_KEY"] = ""

import pytest
from src.models.database import DatabaseManager


@pytest.fixture(autouse=True)
def setup_test_db():
    db = DatabaseManager()
    db.connect()
    db.initialize_schema()
    yield
    db.close()
