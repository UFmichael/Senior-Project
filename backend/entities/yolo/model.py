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
    
    Improvements:
    - Configurable IoU threshold for NMS (reduces duplicate detections)
    - Min/max box size filtering (reduces false positives from tiny/huge boxes)
    - Image preprocessing enhancements
    """
    
    # Weapon class names to identify
    WEAPON_CLASSES = {"gun", "pistol", "rifle", "revolver", "firearm", "knife", "dagger", "machete"}
    
    def __init__(
        self,
        model_path: str = "https://huggingface.co/Subh775/Threat-Detection-YOLOv8n/resolve/main/best.pt",
        device: Optional[str] = None,
        conf: float = 0.30,
        iou: float = 0.45,  
        min_box_area: int = 400,  
        max_box_ratio: float = 10.0,
    ):
        self.device = _select_device(device)
        self.model = YOLO(model_path)
        self.names = self.model.model.names
        self.conf = conf
        self.iou = iou
        self.min_box_area = min_box_area
        self.max_box_ratio = max_box_ratio

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
                        "bbox": [x1, y1, x2, y2],
                        "box_area": int (width * height)
                    }
                ],
                "image_size": (width, height),
                "filtered_count": int (number of detections filtered out)
            }
        """
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        results = self.model(
            img, 
            verbose=False, 
            conf=self.conf, 
            iou=self.iou, 
            device=self.device
        )[0]
        
        detections = []
        filtered_count = 0
        
        for box in results.boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            
            # Calculate box dimensions
            width = x2 - x1
            height = y2 - y1
            box_area = width * height
            aspect_ratio = max(width, height) / (min(width, height) + 1e-6)
            
            # Filter out unrealistic detections
            if box_area < self.min_box_area:
                filtered_count += 1
                continue
            
            if aspect_ratio > self.max_box_ratio:
                filtered_count += 1
                continue
            
            original_class = self.names.get(cls_id, str(cls_id)) if isinstance(self.names, dict) else self.names[cls_id]
            
            is_weapon = original_class.lower() in self.WEAPON_CLASSES
            simplified_class = "weapon" if is_weapon else "non-weapon"
            
            detections.append({
                "class": simplified_class,
                "original_class": original_class,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
                "box_area": int(box_area),
            })
        
        return {
            "detections": detections,
            "image_size": img.size,
            "filtered_count": filtered_count,
        }
