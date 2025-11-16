from typing import Dict, Any, List, Optional
from collections import deque

class Person: 
    def __init__(self, person_id: str, pose_detection: Dict[str, Any], frame_count: int):
        self.id: str = person_id
        self.last_seen_frame: int = frame_count
        
        # Core detection data (updated every frame this person is seen)
        self.pose_bbox: List[float] = pose_detection["bbox"]
        self.pose_confidence: float = pose_detection["confidence"]
        self.keypoints: List[Dict] = pose_detection["keypoints"]
        
        # Correlated data
        self.face: Optional[Dict[str, Any]] = None
        self.weapons: List[Dict[str, Any]] = []
        
        # State and history for advanced logic
        self.emotion_history: deque = deque(maxlen=15) # Store last 15 emotion readings
        self.is_threat: bool = False
        self.threat_reason: str = "none"

    def update_pose(self, pose_detection: Dict[str, Any], frame_count: int):
        """Update the person's state from a new pose detection."""
        self.pose_bbox = pose_detection["bbox"]
        self.pose_confidence = pose_detection["confidence"]
        self.keypoints = pose_detection["keypoints"]
        self.last_seen_frame = frame_count

    def update_correlations(self, 
                            face: Optional[Dict[str, Any]], 
                            weapons: List[Dict[str, Any]]):
        """Update the person's correlated face and weapons for this frame."""
        self.weapons = weapons # Always update with current frame's weapons
        
        if face:
            self.face = face
            emotion = face.get("dominant_emotion", "unknown")
            if emotion != "unknown":
                self.emotion_history.append(emotion)
        else:
            # No face detected for this person this frame
            # We don't clear self.face, just let it persist
            # We can add "unknown" to history to show a gap
            self.emotion_history.append("unknown")

    def get_stable_emotion(self) -> str:
        """Get the most common emotion from the recent history."""
        if not self.emotion_history:
            return "unknown"
        
        # Filter out "unknown" if possible
        known_emotions = [e for e in self.emotion_history if e != "unknown"]
        if not known_emotions:
            return "unknown"
            
        # Return the most frequent emotion
        return max(set(known_emotions), key=known_emotions.count)

    def update_threat_status(self):
        """
        The core logic for this person.
        Determines if this person is currently a threat.
        """
        if self.weapons:
            stable_emotion = self.get_stable_emotion()
            weapon_names = ', '.join([w.get('original_class', 'weapon') for w in self.weapons])
            
            # --- This is where you can build your advanced logic ---
            if stable_emotion in ["angry", "fear"]:
                self.is_threat = True
                self.threat_reason = f"Weapon ({weapon_names}) + Emotion ({stable_emotion})"
            else:
                self.is_threat = True # Weapon is always a threat
                self.threat_reason = f"Weapon ({weapon_names}) detected"
        else:
            self.is_threat = False
            self.threat_reason = "none"

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the person's current state for the WebSocket.
        This maintains the same structure your drawing logic expects.
        """
        return {
            "type": "person",
            "id": self.id,
            "pose_bbox": self.pose_bbox,
            "pose_confidence": self.pose_confidence,
            "keypoints": self.keypoints,
            "face": self.face,
            "weapons": self.weapons,
            
            # Add new state data
            "is_threat": self.is_threat,
            "threat_reason": self.threat_reason,
            "stable_emotion": self.get_stable_emotion()
        }