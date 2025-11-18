# Recent Changes - System Overview

## What Changed?

Your project evolved from a simple **weapon + face detection** system to a sophisticated **person tracking system** with threat assessment. Here's what happened:

---

## Architecture Evolution

### Before (Simple Detection)
```
Stream → Detect Weapons + Faces → Draw boxes → Send to frontend
```

### After (Person Tracking System)
```
Stream → Detect People (pose) + Weapons + Faces
       → Track people across frames
       → Correlate weapons/faces to people
       → Assess threat levels
       → Send structured data to frontend
```

---

## New Components

### 1. **Person Tracker** (`entities/person/services.py`)
**Purpose**: Represents a tracked person across multiple frames

**Key Features**:
- Tracks individual people using pose detection
- Maintains identity across frames
- Stores emotion history (15 frames)
- Correlates weapons and faces to the person
- Calculates threat status

**Person Properties**:
```python
person.id              # Unique identifier (person_0, person_1, etc.)
person.pose_bbox       # Body bounding box
person.keypoints       # Body keypoints (wrists, elbows, etc.)
person.face            # Associated face detection (if any)
person.weapons         # List of weapons held/near this person
person.is_threat       # Boolean: Is this person a threat?
person.threat_reason   # Why they're a threat
```

### 2. **Pose Detection** (YOLOv8-Pose)
**Purpose**: Detect people and their body keypoints

**What it detects**:
- Person bounding boxes
- 17 body keypoints: nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles
- Used to track people and check if weapons are held

### 3. **Correlation Logic** (`services.py`)
**Purpose**: Match weapons and faces to specific people

**How it works**:
1. Detect all people (pose)
2. Detect all weapons
3. Detect all faces
4. For each person:
   - Find closest face (using IoU overlap)
   - Find weapons near their hands (wrist keypoints)
   - Update person with correlated data

### 4. **Threat Assessment** (`Person.update_threat_status()`)
**Current Logic**:
```python
if person has weapon:
    if emotion in ["angry", "fear"]:
        HIGH THREAT: "Weapon + Aggressive Emotion"
    else:
        THREAT: "Weapon detected"
```

---

## File Structure

```
backend/
├── entities/
│   ├── person/
│   │   └── services.py          # Person class (tracking)
│   ├── stream_handler/
│   │   ├── combined_model.py    # Runs all 3 models
│   │   ├── services.py          # Main stream logic + correlation
│   │   ├── utils.py             # Helper functions (IoU, keypoints)
│   │   └── websocket_manager.py # Sends data to frontend
│   ├── yolo/
│   │   └── model.py             # Weapon detection
│   └── face/
│       └── services.py          # Face/emotion detection
```

---

## Data Flow

### Frame Processing Pipeline

```
1. Capture Frame (30 FPS)
   ↓
2. Every 15th frame: Run Pose Detection (YOLOv8-Pose)
   ↓
3. Every 15th frame: Run Weapon Detection (YOLOv8)
   ↓
4. Every 60th frame: Run Face/Emotion Detection (DeepFace)
   ↓
5. Update Person Tracker:
   - Match existing people or create new
   - Correlate faces to people (IoU overlap)
   - Correlate weapons to people (keypoint proximity)
   ↓
6. Run Threat Logic:
   - Each person evaluates their threat status
   - Based on weapons + emotions
   ↓
7. Send to Frontend:
   - Structured person data
   - With threat flags and reasons
   ↓
8. Every 2nd frame: Send annotated frame to WebSocket
```

---

## The Bug You Encountered

### Error
```python
AttributeError: 'list' object has no attribute 'get'
```

### Root Cause
In `utils.py`, the function signature was:
```python
def get_keypoint(person: Dict[str, Any], name: str):
    for kp in person.get("keypoints", []):  # ❌ person is not a dict!
```

But it was being called with:
```python
left_wrist = get_keypoint(person.keypoints, "left_wrist")
                          ^^^^^^^^^^^^^^^^
                          # This is already a LIST!
```

### Fix
Changed the function to accept a list directly:
```python
def get_keypoint(keypoints: List[Dict[str, Any]], name: str):
    for kp in keypoints:  # ✅ Works now!
```

---

## Frontend Impact

The frontend now receives structured person data instead of separate detections:

### Old Format
```json
[
  {"type": "weapon", "bbox": [...], ...},
  {"type": "face", "emotion": "happy", ...}
]
```

### New Format
```json
[
  {
    "type": "person",
    "id": "person_0",
    "pose_bbox": [100, 200, 300, 500],
    "keypoints": [...],
    "face": {"emotion": "happy", "bbox": [...]},
    "weapons": [{"class": "gun", "bbox": [...], "is_held": true}],
    "is_threat": true,
    "threat_reason": "Weapon (gun) + Emotion (angry)"
  }
]
```

---

## Performance Optimizations

| Detection Type | Frequency | Why |
|----------------|-----------|-----|
| Pose (People) | Every 15th frame (2x/sec) | Balance tracking vs speed |
| Weapons | Every 15th frame (2x/sec) | Fast enough for security |
| Face/Emotion | Every 60th frame (0.5x/sec) | Emotions change slowly |
| Frame Send | Every 2nd frame (15 FPS) | Smooth video |

---

## Key Concepts

### 1. **Tracking**
People are tracked across frames using IoU overlap of their bounding boxes. If a person moves slightly, we update the same `Person` object instead of creating a new one.

### 2. **Correlation**
- **Face → Person**: Uses IoU (Intersection over Union) to find which face belongs to which person
- **Weapon → Person**: Uses keypoint proximity (wrist positions) to determine if weapon is held

### 3. **Threat Assessment**
Runs every frame for every person. Considers:
- Presence of weapons
- Emotion history (stable emotion over 15 frames)
- Custom logic (currently includes a test condition)

---

## Common Questions

### Q: Why pose detection instead of just face/weapon?
**A**: Pose gives us:
- Consistent person tracking across frames
- Body keypoints to detect weapon holding
- Better association of faces/weapons to people

### Q: Why different detection frequencies?
**A**: Performance! Running all 3 models every frame would be too slow. We optimize by:
- Running fast models (pose, weapon) more often
- Running slow models (face) less often
- Caching results between detections

### Q: What's IoU?
**A**: Intersection over Union - measures how much two boxes overlap:
- IoU = 1.0 = Perfect overlap
- IoU = 0.5 = 50% overlap
- IoU = 0.0 = No overlap

---

## Next Steps / Future Enhancements

1. **Better Weapon Holding Detection**: Currently uses wrist proximity, could use hand pose
2. **Multi-Person Tracking**: Improve tracking when people occlude each other
3. **Alert History**: Store threat events in database
4. **Configurable Threat Logic**: Make threat assessment rules customizable
5. **Frontend Updates**: Display person tracks, threat indicators, and IDs

---

**Created**: November 17, 2025  
**Status**: System working after bug fix  
**Bug Fixed**: `get_keypoint()` function signature corrected
