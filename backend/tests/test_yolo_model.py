"""
Tests for the YOLO model.
"""
import pytest
import io
import numpy as np
from PIL import Image
from unittest.mock import MagicMock, patch

from entities.yolo.model import YOLOModel


@pytest.fixture
def mock_yolo():
    """Create a mocked YOLO model that doesn't load the actual weights."""
    with patch("entities.yolo.model.YOLO") as mock_yolo_class:
        # Create a mock YOLO instance
        mock_model = MagicMock()
        mock_model.model.names = {0: "person", 1: "weapon"}
        mock_yolo_class.return_value = mock_model
        
        # Return a real YOLOModel instance using the mock YOLO
        model = YOLOModel()
        yield model


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    # Create a simple red image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :] = (255, 0, 0)  # Red color
    
    # Convert to PIL Image then to bytes
    pil_img = Image.fromarray(img)
    img_byte_arr = io.BytesIO()
    pil_img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()


@pytest.mark.asyncio
async def test_yolo_initialization():
    """Test that YOLOModel initializes correctly with default parameters."""
    with patch("entities.yolo.model.YOLO") as mock_yolo:
        # Arrange
        mock_instance = MagicMock()
        mock_instance.model.names = {0: "person", 1: "weapon"}
        mock_yolo.return_value = mock_instance
        
        # Act
        model = YOLOModel()
        
        # Assert
        assert model.model == mock_instance
        assert model.names == {0: "person", 1: "weapon"}
        mock_yolo.assert_called_once_with("https://huggingface.co/Hadi959/weapon-detection-yolov8/resolve/main/best.pt")


@pytest.mark.asyncio
async def test_yolo_predict(mock_yolo, sample_image):
    """Test the prediction functionality of YOLOModel."""
    # Arrange
    mock_results = MagicMock()
    mock_box = MagicMock()
    mock_box.xyxy = [np.array([10.0, 20.0, 30.0, 40.0])]
    mock_box.conf = [np.array([0.95])]
    mock_box.cls = [np.array([0])]  # class 0 = person
    
    mock_results.boxes = [mock_box]
    
    # Configure mock_yolo to return our mocked results
    mock_yolo.model.return_value = [mock_results]
    
    # Act
    result = await mock_yolo.predict(sample_image)
    
    # Assert
    assert "detections" in result
    assert len(result["detections"]) == 1
    
    detection = result["detections"][0]
    assert detection["class"] == "person"
    assert detection["class_id"] == 0
    assert detection["confidence"] == 0.95
    assert detection["bbox"] == [10.0, 20.0, 30.0, 40.0]
    
    assert "image_size" in result
    assert "classes" in result
    assert result["classes"] == {0: "person", 1: "weapon"}
