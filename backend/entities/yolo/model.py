from ultralytics import YOLO
from PIL import Image
import io
from typing import Dict, Any

class YOLOModel:
    def __init__(self, model_path: str = "https://huggingface.co/Hadi959/weapon-detection-yolov8/resolve/main/best.pt"):
        self.model = YOLO(model_path)
        # prefer names from the checkpoint to avoid mismatches
        self.names = self.model.model.names

    async def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        r = self.model(img, verbose=False)[0]
        detections = []
        for box in r.boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            detections.append({
                "class": self.names.get(cls_id, str(cls_id)),
                "class_id": cls_id,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2]
            })
        return {"detections": detections, "image_size": img.size, "classes": self.names}
