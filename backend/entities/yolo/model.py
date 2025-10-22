"""
Simple weapon detection model.
Detects weapons (gun/knife) vs non-weapons (everything else).

Requirements:
    pip install ultralytics pillow torch
"""

import io
from typing import Dict, Any, List, Optional
from PIL import Image
from ultralytics import YOLO
import torch


def _select_device(explicit: Optional[str] = None) -> str:
    """Select best available device for inference."""
    if explicit:
        return explicit
    if torch.cuda.is_available():
        return "0"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class YOLOModel:
    """
    Simple weapon detection model.
    Returns detections classified as either 'weapon' or 'non-weapon'.
    """
    
    # Weapon class names to identify
    WEAPON_CLASSES = {"gun", "pistol", "rifle", "revolver", "firearm", "knife", "dagger", "machete"}
    
    def __init__(
        self,
        model_path: str = "https://huggingface.co/Subh775/Threat-Detection-YOLOv8n/resolve/main/best.pt",
        device: Optional[str] = None,
        conf: float = 0.30,
    ):
        self.device = _select_device(device)
        self.model = YOLO(model_path)
        self.names = self.model.model.names
        self.conf = conf

    async def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Predict objects in image. Returns weapons and non-weapons.
        
        Returns:
            {
                "detections": [
                    {
                        "class": "weapon" or "non-weapon",
                        "original_class": original class name,
                        "confidence": float,
                        "bbox": [x1, y1, x2, y2]
                    }
                ],
                "image_size": (width, height)
            }
        """
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = self.model(img, verbose=False, conf=self.conf, device=self.device)[0]
        
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            
            original_class = self.names.get(cls_id, str(cls_id)) if isinstance(self.names, dict) else self.names[cls_id]
            
            is_weapon = original_class.lower() in self.WEAPON_CLASSES
            simplified_class = "weapon" if is_weapon else "non-weapon"
            
            detections.append({
                "class": simplified_class,
                "original_class": original_class,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
            })
        
        return {
            "detections": detections,
            "image_size": img.size,
        }
