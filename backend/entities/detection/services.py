import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Any
import logging
from datetime import datetime
from uuid import uuid4
import base64
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class YOLODetectionService:
    def __init__(self):
        self.model_path = "yolov8n.pt"
        self.model = None
        self._load_model()
        self.threat_classes = {
            'weapon': ['knife', 'gun', 'rifle', 'pistol', 'bat', 'stick', 'hammer', 'crowbar'],
            'person': ['person'],
            'suspicious_object': ['bag', 'suitcase', 'backpack']
        }

    def _load_model(self):
        try:
            self.model = YOLO(self.model_path)
            logger.info(f"YOLOv8 model loaded: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            raise

    def detect_from_image_file(self, image_path: str, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        results = self.model(image_path, conf=confidence_threshold)
        return self._process_results(results[0], image_path)

    def detect_from_base64(self, base64_image: str, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        image_data = base64.b64decode(base64_image)
        image = Image.open(BytesIO(image_data)).convert("RGB")
        image_np = np.array(image)
        results = self.model(image_np, conf=confidence_threshold)
        return self._process_results(results[0], "base64_image")

    def detect_from_video(self, video_path: str, confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
        results = self.model(video_path, conf=confidence_threshold)
        detections = []
        for i, result in enumerate(results):
            frame_detection = self._process_results(result, f"{video_path}_frame_{i}")
            frame_detection['frame_number'] = i
            detections.append(frame_detection)
        return detections

    def _process_results(self, result, source: str) -> Dict[str, Any]:
        detections, threats_detected = [], []
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
            class_ids = result.boxes.cls.cpu().numpy()
            for i in range(len(boxes)):
                box = boxes[i]
                confidence = float(confidences[i])
                class_id = int(class_ids[i])
                class_name = self.model.names[class_id]
                detection = {
                    'id': str(uuid4()),
                    'class_name': class_name,
                    'class_id': class_id,
                    'confidence': confidence,
                    'bbox': {
                        'x1': float(box[0]),
                        'y1': float(box[1]),
                        'x2': float(box[2]),
                        'y2': float(box[3])
                    },
                    'center': {
                        'x': float((box[0] + box[2]) / 2),
                        'y': float((box[1] + box[3]) / 2)
                    },
                    'area': float((box[2] - box[0]) * (box[3] - box[1]))
                }
                detections.append(detection)
                threat_level = self._assess_threat_level(class_name, confidence)
                if threat_level > 0:
                    threats_detected.append({
                        **detection,
                        'threat_level': threat_level,
                        'threat_category': self._get_threat_category(class_name)
                    })
        return {
            'detection_id': str(uuid4()),
            'source': source,
            'timestamp': datetime.utcnow().isoformat(),
            'total_detections': len(detections),
            'detections': detections,
            'threats_count': len(threats_detected),
            'threats': threats_detected,
            'image_dimensions': {
                'width': int(result.orig_shape[1]) if hasattr(result, "orig_shape") else None,
                'height': int(result.orig_shape[0]) if hasattr(result, "orig_shape") else None
            }
        }

    def _assess_threat_level(self, class_name: str, confidence: float) -> int:
        cname = class_name.lower()
        if cname in ['knife', 'gun', 'rifle', 'pistol', 'bat', 'stick', 'hammer', 'crowbar']:
            return 5 if confidence > 0.8 else 4 if confidence > 0.6 else 3
        elif cname == 'person':
            return 2 if confidence > 0.8 else 1
        elif cname in ['bag', 'suitcase', 'backpack']:
            return 2 if confidence > 0.7 else 1
        return 0

    def _get_threat_category(self, class_name: str) -> str:
        class_lower = class_name.lower()
        for category, classes in self.threat_classes.items():
            if class_lower in [c.lower() for c in classes]:
                return category
        return 'unknown'

    def get_model_info(self) -> Dict[str, Any]:
        if not self.model:
            return {}
        return {
            'model_path': self.model_path,
            'model_type': 'YOLOv8',
            'classes': list(self.model.names.values()),
            'num_classes': len(self.model.names)
        }
