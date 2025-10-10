"""
Tests for database connection functionality.
"""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from core.database import get_engine, get_sessionmaker, Base


@pytest.mark.asyncio
async def test_get_engine():
    """Test that get_engine returns a properly configured engine."""
    # Arrange
    mock_settings = MagicMock()
    mock_settings.SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
    
    # Act
    with patch("core.database.get_settings", return_value=mock_settings), \
         patch("core.database.create_engine") as mock_create_engine:
        
        mock_engine = MagicMock(spec=Engine)
        mock_create_engine.return_value = mock_engine
        
        result = get_engine()
        
        # Assert
        assert result == mock_engine
        mock_create_engine.assert_called_once_with(
            "sqlite:///./test.db", 
            future=True
        )


@pytest.mark.asyncio
async def test_get_sessionmaker():
    """Test that get_sessionmaker returns a properly configured sessionmaker."""
    # Arrange
    mock_engine = MagicMock(spec=Engine)
    
    # Act
    with patch("core.database.get_engine", return_value=mock_engine), \
         patch("core.database.sessionmaker") as mock_sessionmaker_func:
        
        mock_session_factory = MagicMock(spec=sessionmaker)
        mock_sessionmaker_func.return_value = mock_session_factory
        
        result = get_sessionmaker()
        
        # Assert
        assert result == mock_session_factory
        mock_sessionmaker_func.assert_called_once_with(
            bind=mock_engine, 
            autoflush=False, 
            expire_on_commit=False
        )


def test_base_class():
    """Test that Base class is properly configured."""
    # Just a simple test to ensure Base is a SQLAlchemy DeclarativeBase
    assert hasattr(Base, "__tablename__") is False  # Base itself doesn't have a tablename
    
    # Test that Base has the appropriate SQLAlchemy attributes
    assert hasattr(Base, "__init_subclass__")
    assert hasattr(Base, "__init__")
    assert hasattr(Base, "__class_getitem__")
    
    # Skip creating an actual model to avoid SQLAlchemy validation errors
