import os

os.environ["DB_PATH"] = ":memory:"

import pytest
from src.models.database import DatabaseManager


@pytest.fixture(autouse=True)
def setup_test_db():
    db = DatabaseManager()
    db.connect()
    db.initialize_schema()
    yield
    db.close()
