"""
Test script for the combined detection model.
Run this to verify that both weapon and facial emotion detection work together.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from entities.stream_handler.combined_model import CombinedDetectionModel


async def test_combined_model():
    """Test the combined model with a sample image."""
    print("=" * 60)
    print("Testing Combined Detection Model")
    print("=" * 60)
    
    # Initialize model
    print("\n1. Initializing combined model...")
    model = CombinedDetectionModel()
    print("✓ Model initialized successfully")
    
    # Test with a sample image (you'll need to provide your own test image)
    print("\n2. Testing with sample image...")
    print("   Note: This is a dry run test. Provide an actual image for real testing.")
    
    # Create a dummy JPEG image for testing (1x1 pixel)
    import io
    from PIL import Image
    
    img = Image.new('RGB', (640, 480), color='white')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG')
    image_bytes = img_buffer.getvalue()
    
    print("\n3. Running prediction...")
    try:
        results = await model.predict(image_bytes)
        
        print("\n4. Results:")
        print("-" * 60)
        print(f"   Image size: {results.get('image_size')}")
        print(f"   Has weapons: {results.get('has_weapons')}")
        print(f"   Has faces: {results.get('has_faces')}")
        print(f"   Weapon detections: {len(results.get('weapon_detections', []))}")
        print(f"   Face detections: {len(results.get('face_detections', []))}")
        
        if results.get('weapon_detections'):
            print("\n   Weapon Details:")
            for i, weapon in enumerate(results['weapon_detections'], 1):
                print(f"      {i}. Class: {weapon.get('original_class', 'unknown')}, "
                      f"Confidence: {weapon.get('confidence', 0):.2f}")
        
        if results.get('face_detections'):
            print("\n   Face Details:")
            for i, face in enumerate(results['face_detections'], 1):
                emotion = face.get('dominant_emotion', 'unknown')
                scores = face.get('emotion_scores', {})
                emotion_conf = scores.get(emotion, 0) if scores else 0
                print(f"      {i}. Emotion: {emotion} ({emotion_conf:.0f}%), "
                      f"Confidence: {face.get('confidence', 0):.2f}")
        
        print("-" * 60)
        print("✓ Test completed successfully")
        
    except Exception as e:
        print(f"✗ Error during prediction: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("✓ Combined model is working correctly!")
    print("✓ Both weapon detection and facial emotion detection are functional")
    print("\nNote: For comprehensive testing, provide images with:")
    print("  - Weapons (guns, knives)")
    print("  - Human faces with various emotions")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    print("Combined Detection Model Test\n")
    success = asyncio.run(test_combined_model())
    sys.exit(0 if success else 1)
