from ultralytics import YOLO

class YOLOModel:
    def __init__(self):
        # Initialize your YOLO model here
        self.model = None
    
    def load_model(self, model_path: str):
        """Load a trained YOLO model"""
        self.model = YOLO(model_path)
    
    async def predict(self, image):
        """Run inference on an image"""
        if not self.model:
            raise ValueError("Model not loaded")
        results = await self.model(image)
        return results
