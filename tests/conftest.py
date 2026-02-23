import os

test_db_path = "/tmp/test_dandori.db"
os.environ["DB_PATH"] = test_db_path
os.environ["DATABASE_URL"] = ""

import pytest
from src.models.database import DatabaseManager


@pytest.fixture(autouse=True)
def setup_test_db():
    db = DatabaseManager()
    db.connect()
    db.initialize_schema()
    yield
    db.close()
