import cv2
import threading
import time
import asyncio
from .combined_model import CombinedDetectionModel
import numpy as np
from .websocket_manager import manager
from typing import List, Dict, Any, Tuple
from entities.person.services import Person 

# --- IMPORT THE THREAT SERVICE CLASS ---
try:
    from entities.threat.services import ThreatService
except ImportError:
    print("Warning: could not import ThreatService. Disabling database logging.")
    # Create a dummy class that mimics the real one
    class ThreatService:
        def __init__(self):
            print("Running with dummy ThreatService (DB logging disabled).")
        async def log_new_threat(self, person_data: Dict[str, Any], stream_id: str):
            print(f"[SKIPPED DB LOG] Person: {person_data.get('id')} is a threat.")
            await asyncio.sleep(0) # Non-blocking

# (Helper functions calculate_iou, _is_point_in_box, _get_keypoint... no changes)
def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    try:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        unionArea = boxAArea + boxBArea - interArea
        iou = interArea / float(unionArea + 1e-6)
        return iou
    except Exception as e:
        print(f"Error calculating IoU: {e}")
        return 0.0

def _is_point_in_box(px: float, py: float, box: List[float]) -> bool:
    x1, y1, x2, y2 = box
    return x1 <= px <= x2 and y1 <= py <= y2

def _get_keypoint(person_keypoints: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
    for kp in person_keypoints:
        if kp.get("point_name") == name:
            return kp
    return {}


class StreamHandler:
    
    SKELETON_EDGES = [
        ('nose', 'left_eye'), ('nose', 'right_eye'), ('left_eye', 'left_ear'), ('right_eye', 'right_ear'),
        ('left_shoulder', 'right_shoulder'), ('left_shoulder', 'left_hip'), ('right_shoulder', 'right_hip'), ('left_hip', 'right_hip'),
        ('left_shoulder', 'left_elbow'), ('left_elbow', 'left_wrist'),
        ('right_shoulder', 'right_elbow'), ('right_elbow', 'right_wrist'),
        ('left_hip', 'left_knee'), ('left_knee', 'left_ankle'),
        ('right_hip', 'right_knee'), ('right_knee', 'right_ankle')
    ]
    
    def __init__(self, stream_url: str, stream_id: str):
        self.stream_url = stream_url
        self.stream_id = stream_id
        self._thread = None
        self._stop_event = threading.Event()
        self.model = CombinedDetectionModel()
        
        self.last_alert_time = 0
        self.alert_cooldown = 3  # seconds
        
        # --- Person Tracking State ---
        self.tracked_people: Dict[str, Person] = {}
        self.next_person_id: int = 0
        self.max_unseen_frames: int = 45 
        self.min_iou_threshold: float = 0.3 
        
        # --- Database Threat Logging State ---
        self.logged_threat_ids = set()
        
        # --- Instantiate the ThreatService ---
        self.threat_service = ThreatService()

    def _update_person_tracker(self, 
                             results: Dict[str, Any], 
                             frame_count: int) -> List[Dict[str, Any]]:
        """
        Manages the lifecycle of Person objects (tracking, updating, creating, deleting).
        
        Returns:
            A list of dictionaries for all current detections (people + unassigned)
            to be sent to the websocket.
        """
        pose_detections = results.get("pose_detections", [])
        face_detections = results.get("face_detections", [])
        weapon_detections = results.get("weapon_detections", [])

        # --- 1. Match existing people to new pose detections ---
        
        matched_pose_indices = set()
        people_to_update = [] # (person_id, pose_index, iou)

        for person_id, person in self.tracked_people.items():
            best_match_iou = 0.0
            best_match_idx = -1
            
            for i, pose in enumerate(pose_detections):
                if i in matched_pose_indices:
                    continue # This pose is already matched
                
                iou = calculate_iou(person.pose_bbox, pose["bbox"])
                
                if iou > self.min_iou_threshold and iou > best_match_iou:
                    best_match_iou = iou
                    best_match_idx = i
            
            if best_match_idx != -1:
                people_to_update.append((person_id, best_match_idx))
                matched_pose_indices.add(best_match_idx)
        
        # Update matched people
        for person_id, pose_idx in people_to_update:
            self.tracked_people[person_id].update_pose(pose_detections[pose_idx], frame_count)

        # --- 2. Add new people for unmatched poses ---
        for i, pose in enumerate(pose_detections):
            if i not in matched_pose_indices:
                new_id = f"person_{self.next_person_id}"
                self.next_person_id += 1
                new_person = Person(new_id, pose, frame_count)
                self.tracked_people[new_id] = new_person

        # --- 3. Correlate Faces and Weapons to all tracked people ---
        
        available_face_indices = set(range(len(face_detections)))
        available_weapon_indices = set(range(len(weapon_detections)))

        for person_id, person in self.tracked_people.items():
            # We only correlate for people seen this frame
            if person.last_seen_frame != frame_count:
                continue

            # a. Correlate best face
            best_face_match = None
            best_face_idx = -1
            best_face_iou = 0.3 # Min IoU for face-to-person
            
            for i in available_face_indices:
                face = face_detections[i]
                iou = calculate_iou(person.pose_bbox, face["bbox"])
                if iou > best_face_iou:
                    best_face_iou = iou
                    best_face_match = face
                    best_face_idx = i
            
            if best_face_idx != -1:
                available_face_indices.discard(best_face_idx)

            # b. Correlate all matching weapons
            matched_weapons = []
            weapons_to_remove = set()
            for i in available_weapon_indices:
                weapon = weapon_detections[i]
                weapon_box = weapon["bbox"]
                
                # Check for "held"
                left_wrist = _get_keypoint(person.keypoints, "left_wrist")
                right_wrist = _get_keypoint(person.keypoints, "right_wrist")
                
                is_held = False
                if (left_wrist and left_wrist.get("conf", 0) > 0.3 and 
                    _is_point_in_box(left_wrist["x"], left_wrist["y"], weapon_box)):
                    is_held = True
                
                if (not is_held and right_wrist and right_wrist.get("conf", 0) > 0.3 and 
                    _is_point_in_box(right_wrist["x"], right_wrist["y"], weapon_box)):
                    is_held = True
                
                # Check for "near" (overlap)
                is_near = calculate_iou(person.pose_bbox, weapon_box) > 0.05
                
                if is_held or is_near:
                    weapon["is_held"] = is_held
                    matched_weapons.append(weapon)
                    weapons_to_remove.add(i)

            available_weapon_indices -= weapons_to_remove
            
            # c. Update the person object
            person.update_correlations(best_face_match, matched_weapons)

        # --- 4. Run logic, prune old people, and prepare WS data ---
        
        websocket_data = []
        people_to_remove = []

        for person_id, person in self.tracked_people.items():
            if (frame_count - person.last_seen_frame) > self.max_unseen_frames:
                people_to_remove.append(person_id)
            else:
                # This is where the person's internal logic runs
                person.update_threat_status()
                # Add their current state to the websocket message
                websocket_data.append(person.to_dict())

        # Prune dead tracks
        for person_id in people_to_remove:
            print(f"[{self.stream_id}] Removing unseen {person_id}")
            del self.tracked_people[person_id]
            # Clean up logged threat set
            self.logged_threat_ids.discard(person_id) 
        
        # Add unassigned items to websocket data
        for i in available_face_indices:
            face = face_detections[i]
            face["type"] = "face" # Add type for drawing
            websocket_data.append(face)
        
        for i in available_weapon_indices:
            weapon = weapon_detections[i]
            weapon["type"] = "weapon" # Add type for drawing
            websocket_data.append(weapon)
            
        return websocket_data


    # This is the main function that runs continuously in the background thread
    async def _process_stream(self):
        print(f"Handler for '{self.stream_id}' starting: trying to connect to {self.stream_url}")
        
        frame_count = 0
        detection_frame_interval = 15
        face_detection_interval = 60
        display_frame_interval = 2
        last_tracked_data = [] # Cache last tracked data
        
        min_display_interval = 2
        max_display_interval = 4
        last_adaptation_time = time.time()
        adaptation_interval = 5
        
        while not self._stop_event.is_set():
            capture = cv2.VideoCapture(self.stream_url)
            
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            capture.set(cv2.CAP_PROP_FPS, 30)

            if not capture.isOpened():
                print(f"[{self.stream_id}] Error: Stream not available. Retrying in 5 seconds...")
                time.sleep(5)
                continue

            print(f"[{self.stream_id}] Handler connected to stream successfully!")
            
            while not self._stop_event.is_set():
                was_successful, frame = capture.read()
                
                if not was_successful:
                    print(f"[{self.stream_id}] Stream lost. Attempting to reconnect...")
                    break
                
                frame_count += 1
                
                # --- START: DETECTION & TRACKING LOGIC ---
                if frame_count % detection_frame_interval == 0:
                    try:
                        is_success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if not is_success:
                            continue
                            
                        image_bytes = buffer.tobytes()
                        
                        detect_faces = (frame_count % face_detection_interval == 0)
                        
                        results = await self.model.predict(
                            image_bytes, 
                            detect_faces=detect_faces,
                            detect_poses=True # Poses are our anchor, always detect
                        )
                        
                        # --- RE-INJECT OLD FACES IF NOT DETECTING ---
                        # This keeps faces "stuck" to people when not re-scanning
                        if not detect_faces:
                            results["face_detections"] = [
                                p.face for p in self.tracked_people.values() 
                                if p.face is not None
                            ]
                        
                        # --- NEW TRACKING STEP ---
                        last_tracked_data = self._update_person_tracker(results, frame_count)
                        
                        # --- ALERTING & DB LOGGING LOGIC ---
                        current_time = time.time()
                        should_print_console_alert = (current_time - self.last_alert_time) >= self.alert_cooldown
                        
                        has_console_alert = False
                        
                        # We create a list of tasks to run concurrently (e.g., logging to DB)
                        db_logging_tasks = []

                        # 1. Check for Person Threats
                        for item in last_tracked_data:
                            if item.get("type") == "person":
                                person_id = item.get("id")
                                is_threat = item.get("is_threat", False)
                                
                                if is_threat:
                                    # Console Alert (throttled)
                                    if should_print_console_alert:
                                        print(f"🔴 PERSON THREAT [{self.stream_id}]: "
                                              f"{person_id} is a threat. Reason: {item['threat_reason']}")
                                        has_console_alert = True
                                    
                                    # Database Log (state-based)
                                    if person_id not in self.logged_threat_ids:
                                        print(f"⚡️ NEW THREAT DETECTED: {person_id}. Logging to database...")
                                        self.logged_threat_ids.add(person_id)
                                        # Schedule the DB call to run, but don't block
                                        db_logging_tasks.append(
                                            self.threat_service.log_new_threat(item, self.stream_id)
                                        )
                                
                                elif not is_threat and person_id in self.logged_threat_ids:
                                    # Person is no longer a threat, clear them
                                    print(f"✅ Threat cleared for {person_id}.")
                                    self.logged_threat_ids.remove(person_id)
                                    # TODO: You could add another service call here
                                    # to update the threat status to "CLEARED" in the DB
                        
                        # 2. Check for unassigned weapons (Console only)
                        if should_print_console_alert and not has_console_alert:
                            unassigned_weapons = [item for item in last_tracked_data if item.get("type") == "weapon"]
                            if unassigned_weapons:
                                print(f"🟡 UNASSIGNED WEAPON [{self.stream_id}]: "
                                      f"{len(unassigned_weapons)} weapon(s) detected.")
                                has_console_alert = True
                        
                        if has_console_alert:
                            self.last_alert_time = current_time
                        
                        # Run any scheduled DB tasks concurrently
                        if db_logging_tasks:
                            await asyncio.gather(*db_logging_tasks)

                    except Exception as e:
                        print(f"[{self.stream_id}] Error processing frame: {e}")
                        import traceback
                        traceback.print_exc()
                # --- END: DETECTION & TRACKING LOGIC ---
                
                
                # --- Adaptive frame rate (no change) ---
                current_time = time.time()
                if current_time - last_adaptation_time >= adaptation_interval:
                    slow_ratio = manager.get_slow_client_ratio(self.stream_id)
                    if slow_ratio > 0.7:
                        display_frame_interval = min(display_frame_interval + 1, max_display_interval)
                    elif slow_ratio < 0.1 and display_frame_interval > min_display_interval:
                        display_frame_interval = max(display_frame_interval - 1, min_display_interval)
                    last_adaptation_time = current_time
                
                
                # --- Drawing Logic (no change) ---
                if frame_count % display_frame_interval == 0 and manager.has_connections(self.stream_id):
                    try:
                        annotated_frame = frame.copy()
                        
                        # This logic works perfectly with our new person.to_dict()
                        for detection in last_tracked_data:
                            det_type = detection.get("type", "unknown")

                            # --- Draw Correlated Person ---
                            if det_type == "person":
                                keypoints = detection.get("keypoints", [])
                                keypoints_dict = {kp["point_name"]: kp for kp in keypoints}

                                # 1. Draw Skeleton Lines
                                pose_line_color = (255, 255, 0) # Cyan
                                for p1_name, p2_name in self.SKELETON_EDGES:
                                    kp1 = keypoints_dict.get(p1_name)
                                    kp2 = keypoints_dict.get(p2_name)
                                    if kp1 and kp2 and kp1.get("conf", 0) > 0.3 and kp2.get("conf", 0) > 0.3:
                                        pt1 = (int(kp1["x"]), int(kp1["y"]))
                                        pt2 = (int(kp2["x"]), int(kp2["y"]))
                                        cv2.line(annotated_frame, pt1, pt2, pose_line_color, 2)
                                
                                # 2. Draw Keypoint Circles
                                pose_point_color = (0, 255, 255) # Yellow
                                for kp in keypoints:
                                    if kp.get("conf", 0) > 0.3:
                                        x, y = int(kp["x"]), int(kp["y"])
                                        cv2.circle(annotated_frame, (x, y), 4, pose_point_color, -1)

                                # Draw Person Pose Box
                                pose_box = detection.get("pose_bbox", [])
                                if pose_box:
                                    x1, y1, x2, y2 = map(int, pose_box)
                                    # --- Color box based on threat level ---
                                    color = (0, 0, 255) if detection.get("is_threat") else (0, 255, 0) # RED if threat, else GREEN
                                    
                                    label = f"{detection['id']}: {detection['stable_emotion']}"
                                    if detection.get("is_threat"):
                                        label = f"{detection['id']} (THREAT!)"
                                    
                                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                                
                                # Draw Face Box (if it exists)
                                if detection["face"]:
                                    face_box = detection["face"].get("bbox", [])
                                    if face_box:
                                        fx1, fy1, fx2, fy2 = map(int, face_box)
                                        cv2.rectangle(annotated_frame, (fx1, fy1), (fx2, fy2), (255, 0, 0), 2)
                                
                                # Draw Weapon Boxes (if they exist)
                                for weapon in detection.get("weapons", []):
                                    weapon_box = weapon.get("bbox", [])
                                    if weapon_box:
                                        wx1, wy1, wx2, wy2 = map(int, weapon_box)
                                        w_label = f"{weapon.get('original_class', 'weapon')}"
                                        cv2.rectangle(annotated_frame, (wx1, wy1), (wx2, wy2), (0, 0, 255), 2)
                                        cv2.putText(annotated_frame, w_label, (wx1, wy1 - 10),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                            
                            # --- Draw Unassigned Weapon ---
                            elif det_type == "weapon":
                                bbox = detection.get("bbox", [])
                                if bbox:
                                    x1, y1, x2, y2 = map(int, bbox)
                                    color = (0, 165, 255) # ORANGE
                                    label = f"UNASSIGNED {detection.get('original_class', 'weapon')}"
                                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                            # --- Draw Unassigned Face ---
                            elif det_type == "face":
                                bbox = detection.get("bbox", [])
                                if bbox:
                                    x1, y1, x2, y2 = map(int, bbox)
                                    color = (255, 255, 0) # CYAN
                                    label = f"UNASSIGNED {detection.get('dominant_emotion', 'Face')}"
                                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                        # Encode and send frame
                        is_success, encoded_frame = cv2.imencode(".jpg", annotated_frame, 
                                                                 [cv2.IMWRITE_JPEG_QUALITY, 60])
                        if is_success:
                            frame_bytes = encoded_frame.tobytes()
                            await manager.send_frame(
                                stream_id=self.stream_id,
                                frame_data=frame_bytes,
                                detections=last_tracked_data # Send the new tracked data
                            )
                    except Exception as e:
                        print(f"[{self.stream_id}] Error sending frame to WebSocket (non-critical): {e}")
                # --- END: DRAWING LOGIC ---
                
                # Periodically send pings
                if frame_count % 300 == 0:
                    await manager.send_ping(self.stream_id)
            
            capture.release()
            
        print(f"Handler for '{self.stream_id}' has been stopped.")

    # --- start, stop, is_running methods (Unchanged) ---
    def start(self) -> bool:
        if self.is_running():
            print("Handler is already running.")
            return False
        self._stop_event.clear()
        
        async def run_async():
            await self._process_stream()
            
        def thread_target():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_async())
            loop.close()
        
        self._thread = threading.Thread(target=thread_target, daemon=True)
        self._thread.start()

        print(f"Stream handler for '{self.stream_id}' started.")
        return True

    def stop(self) -> bool:
        if not self.is_running():
            print("Handler is not running.")
            return False
        self._stop_event.set()
        
        # Check if thread exists before joining
        if self._thread:
            self._thread.join(timeout=5)
        
        if self._thread and self._thread.is_alive():
            print("Error: Handler thread did not stop in time.")
            return False
        
        print(f"Stream handler for '{self.stream_id}' stopped successfully.")
        return True

    def is_running(self) -> bool:
        return self._thread and self._thread.is_alive()

# --- Global handler management (unchanged) ---
stream_handlers = {}
_lock = threading.Lock()

def start_stream_processing(stream_id: str):
    with _lock:
        if stream_id in stream_handlers and stream_handlers[stream_id].is_running():
            return False

        stream_url = f"rtmp://127.0.0.1:1935/live/{stream_id}"
        handler = StreamHandler(stream_url=stream_url, stream_id=stream_id)
        stream_handlers[stream_id] = handler
        
        return handler.start()

def stop_stream_processing(stream_id: str):
    with _lock:
        if stream_id not in stream_handlers or not stream_handlers[stream_id].is_running():
            return False
        
        success = stream_handlers[stream_id].stop()
        if success:
            del stream_handlers[stream_id]
        
        return success