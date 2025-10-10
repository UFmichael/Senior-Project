"""
Tests for the authentication router.
"""
import pytest
import uuid
from datetime import timedelta
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

from entities.auth.router import login


@pytest.fixture
def mock_user():
    """Create a mock user for testing authentication."""
    # fake user so we don't mess up database
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.username = "testuser"
    mock_user.hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # hashed version of 'secret'
    return mock_user


@pytest.mark.asyncio
async def test_login_success(mock_user):
    """Test successful login with correct credentials."""
    form_data = MagicMock()
    form_data.username = "testuser"
    form_data.password = "secret"
    
    db = MagicMock()
    
    # mocking the authenticate_user function to return our mock user
    with patch("entities.auth.router.authenticate_user") as mock_auth, \
         patch("entities.auth.router.get_settings") as mock_settings, \
         patch("entities.auth.router.create_access_token") as mock_access_token, \
         patch("entities.auth.router.create_refresh_token") as mock_refresh_token:
        
        mock_auth.return_value = mock_user
    
        settings = MagicMock()
        settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        settings.REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week
        mock_settings.return_value = settings

        mock_access_token.return_value = "mock-access-token"
        mock_refresh_token.return_value = "mock-refresh-token"
        
        result = login(form_data, db)
        
        assert result.access_token == "mock-access-token"
        assert result.refresh_token == "mock-refresh-token"
        assert result.token_type == "bearer"
        assert result.expires_in == 1800  # 30 minutes in seconds
        
        # verify everything works as expected
        mock_auth.assert_called_once_with(db, "testuser", "secret")
        mock_access_token.assert_called_once_with(subject=mock_user.id, expires_delta=timedelta(minutes=30))
        mock_refresh_token.assert_called_once_with(subject=mock_user.id, expires_delta=timedelta(minutes=60*24*7))


@pytest.mark.asyncio
async def test_login_failure():
    """Test login failure with incorrect credentials."""
    form_data = MagicMock()
    form_data.username = "testuser"
    form_data.password = "wrongpassword"
    
    db = MagicMock()
    
    # Mock the authenticate_user function to return None (authentication failure)
    with patch("entities.auth.router.authenticate_user") as mock_auth:
        mock_auth.return_value = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            login(form_data, db)
            
        # Check that the exception has the correct status code and detail
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Incorrect username or password"
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
        
        # Verify mock was called correctly
        mock_auth.assert_called_once_with(db, "testuser", "wrongpassword")
