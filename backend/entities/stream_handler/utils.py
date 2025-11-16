from typing import List, Dict, Any

def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    Boxes are [x1, y1, x2, y2].
    """
    try:
        # Determine the (x, y)-coordinates of the intersection rectangle
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        # Compute the area of intersection
        interArea = max(0, xB - xA) * max(0, yB - yA)

        # Compute the area of both bounding boxes
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        # Compute the union area
        unionArea = boxAArea + boxBArea - interArea

        # Compute the IoU
        iou = interArea / float(unionArea + 1e-6) # Avoid division by zero
        return iou
    except Exception as e:
        print(f"Error calculating IoU: {e}")
        return 0.0

def is_point_in_box(px: float, py: float, box: List[float]) -> bool:
    """Check if a point (px, py) is inside a bounding box [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = box
    return x1 <= px <= x2 and y1 <= py <= y2

def get_keypoint(person: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Get a specific keypoint by name from a person's keypoints list."""
    for kp in person.get("keypoints", []):
        if kp.get("point_name") == name:
            return kp
    return {}