"""
This file contains shared test fixtures and configurations.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from main import app
from core.database import Base
from core.dependencies import get_db

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database for each test.
    """
    # Create the test database and tables
    Base.metadata.create_all(bind=engine)
    
    # Create a db session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up after the test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Create a FastAPI TestClient that uses the db fixture.
    """
    def _get_test_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as c:
        yield c
        
    # Reset any overrides after the test
    app.dependency_overrides = {}


@pytest.fixture(scope="function")
def mock_yolo_model(monkeypatch):
    """
    Mock the YOLOModel class to avoid loading the actual model during tests.
    """
    class MockYOLOModel:
        def __init__(self):
            pass
            
        async def predict(self, image_bytes):
            return {"objects": [{"class": "person", "confidence": 0.95, "bbox": [10, 10, 50, 50]}]}
    
    from entities.yolo.model import YOLOModel
    monkeypatch.setattr("entities.yolo.model.YOLOModel", MockYOLOModel)
    return MockYOLOModel()
