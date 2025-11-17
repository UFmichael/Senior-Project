from deepface import DeepFace 
from PIL import Image 
import io 
from typing import Dict, Any
import numpy as np
import asyncio
import cv2

# TODO Make schemas for the predicitons so that we can have defined types throughout the project, right now I am defining objects in each function
class FaceModel: 
    # Face model for making predicitons based 
    def __init__(self, actions: list[str] = ['age', 'gender', 'emotion'], model_type: str = "Facenet512" ) -> None:
        self.model = DeepFace
        self.actions = actions
        self.model_type = model_type

        try:
            print("Loading DeepFace models...")
            DeepFace.build_model(model_name=model_type)
            print("DeepFace model loaded successfully.")
        except Exception as e:
            print(f"Warning: Could not pre-load DeepFace models. They will be loaded on first predict(). Error: {e}")

    # Prediction function (Trying to kind of mimic YOLO)        
    async def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            
            img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_size = img_pil.size  
            
            img_np_rgb = np.array(img_pil)
            img_np_bgr = cv2.cvtColor(img_np_rgb, cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            return {"error": f"Failed to process image bytes: {e}", "detections": [], "image_size": [0, 0]}

        #  DeepFace analysis
        try:
            # Different thread 
            results = await asyncio.to_thread(
                DeepFace.analyze,
                img_path=img_np_bgr,
                actions=self.actions,
                enforce_detection=False  
            )

        except Exception as e:
            return {"error": f"DeepFace analysis failed: {e}", "detections": [], "image_size": img_size}

        detections = []
        
        for face_data in results:
            if "region" not in face_data:
                continue

            # Bbox for the face, can probably store this in a database 
            region = face_data["region"]
            x1 = float(region["x"])
            y1 = float(region["y"])
            x2 = float(region["x"] + region["w"])
            y2 = float(region["y"] + region["h"])
            
            confidence = float(face_data.get("face_confidence", 1.0))
            
            analysis_data = {
                "dominant_emotion": face_data.get("dominant_emotion"),
                "race": face_data.get("race"),
                "emotion_scores": face_data.get("emotion"),
                "age": face_data.get("age"),
                "dominant_gender": face_data.get("dominant_gender"),
                "gender_scores": face_data.get("gender"),
            }
            
            # Not sure if this is the type that we want to be returning, most likely will have to come up with a schema for this
            detections.append({
                "confidence": confidence,  
                "bbox": [x1, y1, x2, y2],
                "analysis": analysis_data  
            })

        return {
            "detections": detections,
            "image_size": img_size,
        }

