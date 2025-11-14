"""
Combined detection model for weapon detection and facial emotion analysis.
Runs both YOLO weapon detection and DeepFace emotion detection on the same frame.
"""

import asyncio
from typing import Dict, Any, List
from entities.yolo.model import YOLOModel
from entities.face.services import FaceModel


class CombinedDetectionModel:
    """
    Combined model that performs both weapon detection and facial emotion detection.
    Optimized to run both models concurrently for better performance.
    """
    
    def __init__(self):
        """Initialize both weapon detection and face emotion detection models."""
        self.weapon_model = YOLOModel()
        self.face_model = FaceModel(
            actions=['emotion'],  # Only detect emotions for performance
            model_type="Facenet512"
        )
        print("Combined Detection Model initialized (Weapon + Face Emotion)")
    
    async def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Run both weapon detection and facial emotion detection concurrently.
        
        Args:
            image_bytes: JPEG image as bytes
            
        Returns:
            {
                "weapon_detections": [...],
                "face_detections": [...],
                "image_size": (width, height),
                "has_weapons": bool,
                "has_faces": bool
            }
        """
        try:
            # Run both models concurrently for better performance
            weapon_results, face_results = await asyncio.gather(
                self.weapon_model.predict(image_bytes),
                self.face_model.predict(image_bytes),
                return_exceptions=True
            )
            
            # Handle weapon detection results
            weapon_detections = []
            if isinstance(weapon_results, dict) and "detections" in weapon_results:
                weapon_detections = [
                    det for det in weapon_results["detections"]
                    if det.get("class") == "weapon"  # Only include actual weapons
                ]
            elif isinstance(weapon_results, Exception):
                print(f"Weapon detection error: {weapon_results}")
            
            # Handle face detection results
            face_detections = []
            if isinstance(face_results, dict) and "detections" in face_results:
                for face in face_results["detections"]:
                    analysis = face.get("analysis", {})
                    face_detections.append({
                        "bbox": face.get("bbox", []),
                        "confidence": face.get("confidence", 0.0),
                        "dominant_emotion": analysis.get("dominant_emotion", "unknown"),
                        "emotion_scores": analysis.get("emotion_scores", {}),
                    })
            elif isinstance(face_results, Exception):
                print(f"Face detection error: {face_results}")
            
            # Get image size from either result
            image_size = (0, 0)
            if isinstance(weapon_results, dict):
                image_size = weapon_results.get("image_size", (0, 0))
            elif isinstance(face_results, dict):
                image_size = face_results.get("image_size", (0, 0))
            
            return {
                "weapon_detections": weapon_detections,
                "face_detections": face_detections,
                "image_size": image_size,
                "has_weapons": len(weapon_detections) > 0,
                "has_faces": len(face_detections) > 0,
            }
            
        except Exception as e:
            print(f"Error in combined prediction: {e}")
            import traceback
            traceback.print_exc()
            return {
                "weapon_detections": [],
                "face_detections": [],
                "image_size": (0, 0),
                "has_weapons": False,
                "has_faces": False,
                "error": str(e)
            }
