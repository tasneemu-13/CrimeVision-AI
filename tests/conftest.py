"""
Pytest configuration fixture for isolated test database.
"""
import os
import tempfile
import pytest

from database.connection import Base, engine, init_db


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure database schema is fresh for each test run."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
