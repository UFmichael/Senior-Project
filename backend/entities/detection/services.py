import ultralytics
import supervision
import torch
import cv2
from collections import defaultdict
import supervision as sv
from ultralytics import YOLO
import os

class WeaponDetector:
    def __init__(self, model_path='yolov8n.pt'):
        print("Loading YOLOv8 model")
        self.model = YOLO(model_path)
        self.weapon_classes = [43, 76]
        
    def detect_weapons(self, image_path, conf_threshold=0.5, save_result=True):
        if not os.path.exists(image_path):
            print(f"Error: Image not found at {image_path}")
            return False, 0
        
        image = cv2.imread(image_path)
        
        results = self.model.predict(
            source=image,
            conf=conf_threshold,
            classes=self.weapon_classes,
            save=save_result
        )
        
        detections = results[0].boxes
        weapon_count = len(detections)
        weapon_detected = weapon_count > 0
        
        annotated_image = results[0].plot()
        
        if weapon_detected:
            print(f"WARNING: {weapon_count} weapon(s) detected")
            for i, box in enumerate(detections):
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = self.model.names[class_id]
                print(f"{class_name} (confidence: {confidence:.2f})")
        else:
            print("No weapons detected")
        
        if save_result:
            output_path = f"weapon_detection_{os.path.basename(image_path)}"
            cv2.imwrite(output_path, annotated_image)
            print(f"Annotated image saved to: {output_path}")
        
        cv2.imshow('Weapon Detection', annotated_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        return weapon_detected, weapon_count
    
    def detect_all_objects(self, image_path, conf_threshold=0.5):
        """
        Detect all objects in image (useful for testing)
        
        Args:
            image_path: Path to input image
            conf_threshold: Confidence threshold for detection
        """
        results = self.model.predict(
            source=image_path,
            conf=conf_threshold,
            save=True
        )
        
        detections = results[0].boxes
        print(f"\nDetected {len(detections)} objects:")
        for box in detections:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = self.model.names[class_id]
            print(f"  - {class_name} (ID: {class_id}, confidence: {confidence:.2f})")


def main():
    """
    Main function to run weapon detection
    """
    # Initialize detector
    detector = WeaponDetector(model_path='yolov8n.pt')
    
    # Path to your image
    image_path = "test_image.jpg"  # Change this to your image path
    
    # Detect weapons
    print(f"\nAnalyzing image: {image_path}")
    print("-" * 50)
    
    weapon_detected, count = detector.detect_weapons(
        image_path=image_path,
        conf_threshold=0.3,  # Lower threshold for better detection
        save_result=True
    )
    
    # Optional: Uncomment to see all detected objects
    # print("\n" + "="*50)
    # print("ALL OBJECTS DETECTED:")
    # detector.detect_all_objects(image_path, conf_threshold=0.3)


if __name__ == "__main__":
    main()