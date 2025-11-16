import cv2
import threading
import time
import asyncio
from .combined_model import CombinedDetectionModel
import numpy as np
from .websocket_manager import manager
from .utils import *
from typing import Dict, Any, List, Tuple

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
        # Stores the RTMP stream URL that this handler will connect to
        self.stream_url = stream_url
        self.stream_id = stream_id
        self._thread = None
        # A threading.Event object that acts as a safe flag to signal the thread when to stop
        self._stop_event = threading.Event()
        self.model = CombinedDetectionModel()
        
        # Alert throttling - prevent spamming console with alerts
        self.last_alert_time = 0
        self.alert_cooldown = 3  # seconds between alerts

    
    def _correlate_detections(self, results: Dict[str, Any]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Correlates poses, faces, and weapons into "person" objects.
        
        Returns:
            (correlated_people, unassigned_weapons, unassigned_faces)
        """
        pose_detections = results.get("pose_detections", [])
        face_detections = results.get("face_detections", [])
        weapon_detections = results.get("weapon_detections", [])

        correlated_people = []
        used_face_indices = set()
        used_weapon_indices = set()

        # --- 1. Create base "person" objects from pose detections ---
        for i, pose in enumerate(pose_detections):
            correlated_people.append({
                "type": "person",
                "id": f"person_{i}",
                "pose_bbox": pose["bbox"],
                "pose_confidence": pose["confidence"],
                "keypoints": pose["keypoints"],
                "face": None,
                "weapons": []
            })

        # --- 2. Correlate Faces to People ---
        for j, face in enumerate(face_detections):
            best_match_iou = 0.3  # Min IoU to be considered a match
            best_match_person = None
            
            for person in correlated_people:
                iou = calculate_iou(person["pose_bbox"], face["bbox"])
                
                # Check if this face is a better match for this person
                if iou > best_match_iou:
                    # And check if this person doesn't already have a better-matched face
                    if not person["face"] or iou > person["face"]["_iou"]:
                        best_match_iou = iou
                        best_match_person = person
            
            if best_match_person:
                # If this person already had a face, that face is now unassigned
                # (This is rare but handles overlapping poses)
                
                # Assign this face to the best matching person
                face["_iou"] = best_match_iou # Store IoU for potential replacement
                best_match_person["face"] = face
                used_face_indices.add(j)

        # --- 3. Correlate Weapons to People ---
        for k, weapon in enumerate(weapon_detections):
            weapon_box = weapon["bbox"]
            best_match_person = None
            is_held = False

            for person in correlated_people:
                person_box = person["pose_bbox"]
                
                # Check for "held" (wrist in weapon box)
                # This is a very strong correlation
                left_wrist = get_keypoint(person, "left_wrist")
                right_wrist = get_keypoint(person, "right_wrist")
                
                if (left_wrist and left_wrist.get("conf", 0) > 0.3 and 
                    is_point_in_box(left_wrist["x"], left_wrist["y"], weapon_box)):
                    is_held = True
                
                if (not is_held and right_wrist and right_wrist.get("conf", 0) > 0.3 and 
                    is_point_in_box(right_wrist["x"], right_wrist["y"], weapon_box)):
                    is_held = True

                if is_held:
                    best_match_person = person
                    break # Stop checking other people if it's held
                
                # Check for "near" (simple overlap)
                iou = calculate_iou(person_box, weapon_box)
                if iou > 0.05: # Even a small overlap is a good indicator
                    best_match_person = person
                    # Don't break, keep checking if another person is "holding" it

            if best_match_person:
                weapon["is_held"] = is_held
                best_match_person["weapons"].append(weapon)
                used_weapon_indices.add(k)

        # --- 4. Collect Unassigned Detections ---
        unassigned_weapons = [w for i, w in enumerate(weapon_detections) if i not in used_weapon_indices]
        for w in unassigned_weapons: w["type"] = "weapon" # Add type for drawing
        
        unassigned_faces = [f for i, f in enumerate(face_detections) if i not in used_face_indices]
        for f in unassigned_faces: f["type"] = "face" # Add type for drawing

        # Clean up temporary _iou key from faces
        for person in correlated_people:
            if person["face"] and "_iou" in person["face"]:
                del person["face"]["_iou"]
        
        return correlated_people, unassigned_weapons, unassigned_faces

    # This is the main function that runs continuously in the background thread
    async def _process_stream(self):
        print(f"Handler for '{self.stream_id}' starting: trying to connect to {self.stream_url}")
        
        # Frame skipping and timing control with adaptive frame rate
        frame_count = 0
        detection_frame_interval = 15  # Process weapon detection every 15th frame - MORE OPTIMIZED
        face_detection_interval = 60   # Process face detection every 60th frame (once per 2 seconds)
        display_frame_interval = 2     # Send to frontend (starts at ~15 FPS from 30 FPS source)
        last_detections = []  # Cache last detection results
        
        # Adaptive frame rate parameters - LESS AGGRESSIVE
        min_display_interval = 2  # Start higher (max 15 FPS instead of 30)
        max_display_interval = 4  # Lower max (min 7.5 FPS instead of 5)
        last_adaptation_time = time.time()
        adaptation_interval = 5  # Adjust every 5 seconds (was 3) - less frequent changes
        
        # This is the outer reconnection loop, keeps running as long as the stop event isn't set
        while not self._stop_event.is_set():
            capture = cv2.VideoCapture(self.stream_url)
            
            # Optimize video capture settings
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
            capture.set(cv2.CAP_PROP_FPS, 30)

            # If the connection fails, wait 5 seconds to try reconnecting
            if not capture.isOpened():
                print(f"[{self.stream_id}] Error: Stream not available. Retrying in 5 seconds...")
                time.sleep(5)
                continue

            print(f"[{self.stream_id}] Handler connected to stream successfully!")
            
            while not self._stop_event.is_set():
                was_successful, frame = capture.read()
                
                # Runs if the stream has been lost or has ended.
                if not was_successful:
                    print(f"[{self.stream_id}] Stream lost. Attempting to reconnect...")
                    break
                
                frame_count += 1
                
                # Process frame with combined model only every Nth frame
                # Face detection runs less frequently than weapon detection for better performance
                if frame_count % detection_frame_interval == 0:
                    try:
                        is_success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if not is_success:
                            continue
                            
                        image_bytes = buffer.tobytes()
                        
                        # Decide whether to run face detection on this frame
                        detect_faces = (frame_count % face_detection_interval == 0)
                        
                        # Always detect weapons and poses (poses are our "person" anchor)
                        results = await self.model.predict(
                            image_bytes, 
                            detect_faces=detect_faces,
                            detect_poses=True
                        )
                        
                        # --- NEW CORRELATION STEP ---
                        # If we didn't detect faces, reuse old face data for correlation
                        if not detect_faces:
                            previous_face_detections = [d for d in last_detections if d.get("type") == "face"]
                            results["face_detections"] = previous_face_detections
                        
                        (correlated_people, 
                         unassigned_weapons, 
                         unassigned_faces) = self._correlate_detections(results)
                        
                        # Store all correlated/unassigned items for drawing
                        last_detections = correlated_people + unassigned_weapons + unassigned_faces
                        
                        # NEW ALERTING LOGIC 
                        current_time = time.time()
                        should_print_alert = (current_time - self.last_alert_time) >= self.alert_cooldown
                        
                        if should_print_alert:
                            has_alert = False
                            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

                            # 1. Check for correlated threats (Person + Weapon)
                            for person in correlated_people:
                                if person["weapons"]:
                                    has_alert = True
                                    weapon_names = ', '.join([w.get('original_class', 'weapon') for w in person["weapons"]])
                                    emotion = "unknown"
                                    if person["face"]:
                                        emotion = person["face"].get('dominant_emotion', 'unknown')
                                    
                                    print(f"🔴 PERSON THREAT [{self.stream_id} @ {timestamp}]: "
                                          f"Person detected with {weapon_names}. "
                                          f"Emotion: {emotion}.")
                            
                            # 2. Check for unassigned weapons
                            if not has_alert and unassigned_weapons:
                                has_alert = True
                                print(f"🟡 UNASSIGNED WEAPON [{self.stream_id} @ {timestamp}]: "
                                      f"{len(unassigned_weapons)} weapon(s) detected without a person.")
                            
                            if has_alert:
                                self.last_alert_time = current_time

                    except Exception as e:
                        print(f"[{self.stream_id}] Error processing frame: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Adaptive frame rate adjustment based on client performance
                current_time = time.time()
                if current_time - last_adaptation_time >= adaptation_interval:
                    slow_ratio = manager.get_slow_client_ratio(self.stream_id)
                    
                    # More conservative thresholds to prevent frame rate oscillation
                    if slow_ratio > 0.7:  # More than 70% of clients are slow (was 50%)
                        # Decrease frame rate (increase interval)
                        display_frame_interval = min(display_frame_interval + 1, max_display_interval)
                        print(f"[{self.stream_id}] Decreased frame rate due to slow clients ({slow_ratio:.1%}). New interval: {display_frame_interval}")
                    elif slow_ratio < 0.1 and display_frame_interval > min_display_interval:
                        # Increase frame rate (decrease interval) only if clients are very fast (was 20%)
                        display_frame_interval = max(display_frame_interval - 1, min_display_interval)
                        print(f"[{self.stream_id}] Increased frame rate. New interval: {display_frame_interval}")
                    
                    last_adaptation_time = current_time
                
                # Send frame to WebSocket clients only every display_frame_interval frames
                # and only if there are active connections
                # --- START: MODIFIED DRAWING LOGIC ---
                if frame_count % display_frame_interval == 0 and manager.has_connections(self.stream_id):
                    try:
                        annotated_frame = frame.copy()
                        
                        for detection in last_detections:
                            det_type = detection.get("type", "unknown")

                            # --- Draw Correlated Person ---
                            if det_type == "person":
                                
                                # --- START: NEW POSE DRAWING ---
                                keypoints = detection.get("keypoints", [])
                                # Create a quick lookup dictionary for keypoints
                                keypoints_dict = {kp["point_name"]: kp for kp in keypoints}

                                # 1. Draw Skeleton Lines
                                pose_line_color = (255, 255, 0) # Cyan
                                for p1_name, p2_name in self.SKELETON_EDGES:
                                    kp1 = keypoints_dict.get(p1_name)
                                    kp2 = keypoints_dict.get(p2_name)
                                    
                                    # Check if both keypoints exist and are confident
                                    if kp1 and kp2 and kp1.get("conf", 0) > 0.3 and kp2.get("conf", 0) > 0.3:
                                        pt1 = (int(kp1["x"]), int(kp1["y"]))
                                        pt2 = (int(kp2["x"]), int(kp2["y"]))
                                        cv2.line(annotated_frame, pt1, pt2, pose_line_color, 2)
                                
                                # 2. Draw Keypoint Circles
                                pose_point_color = (0, 255, 255) # Yellow
                                for kp in keypoints:
                                    if kp.get("conf", 0) > 0.3: # Draw only confident keypoints
                                        x, y = int(kp["x"]), int(kp["y"])
                                        cv2.circle(annotated_frame, (x, y), 4, pose_point_color, -1) # -1 thickness = filled
                                # --- END: NEW POSE DRAWING ---

                                # Draw Person Pose Box
                                pose_box = detection.get("pose_bbox", [])
                                if pose_box:
                                    x1, y1, x2, y2 = map(int, pose_box)
                                    color = (0, 255, 0) # GREEN for person
                                    label = "Person"
                                    
                                    # Add emotion to label if face exists
                                    if detection["face"]:
                                        emotion = detection["face"].get("dominant_emotion", "??")
                                        label = f"Person: {emotion}"
                                    
                                    # Draw box and label
                                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                                
                                # Draw Face Box (if it exists)
                                if detection["face"]:
                                    face_box = detection["face"].get("bbox", [])
                                    if face_box:
                                        fx1, fy1, fx2, fy2 = map(int, face_box)
                                        cv2.rectangle(annotated_frame, (fx1, fy1), (fx2, fy2), (255, 0, 0), 2) # BLUE for face
                                
                                # Draw Weapon Boxes (if they exist)
                                for weapon in detection.get("weapons", []):
                                    weapon_box = weapon.get("bbox", [])
                                    if weapon_box:
                                        wx1, wy1, wx2, wy2 = map(int, weapon_box)
                                        w_label = f"{weapon.get('original_class', 'weapon')}: {weapon['confidence']:.2f}"
                                        cv2.rectangle(annotated_frame, (wx1, wy1), (wx2, wy2), (0, 0, 255), 2) # RED for weapon
                                        cv2.putText(annotated_frame, w_label, (wx1, wy1 - 10),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                            
                            # --- Draw Unassigned Weapon ---
                            elif det_type == "weapon":
                                bbox = detection.get("bbox", [])
                                if bbox:
                                    x1, y1, x2, y2 = map(int, bbox)
                                    color = (0, 165, 255) # ORANGE for unassigned weapon
                                    label = f"UNASSIGNED {detection.get('original_class', 'weapon')}"
                                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                            # --- Draw Unassigned Face ---
                            elif det_type == "face":
                                bbox = detection.get("bbox", [])
                                if bbox:
                                    x1, y1, x2, y2 = map(int, bbox)
                                    color = (255, 255, 0) # CYAN for unassigned face
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
                                detections=last_detections # Send the new correlated data
                            )
                    except Exception as e:
                        print(f"[{self.stream_id}] Error sending frame to WebSocket (non-critical): {e}")
                # --- END: MODIFIED DRAWING LOGIC ---
                
                # Periodically send pings to keep connections alive
                if frame_count % 300 == 0:  # Every ~10 seconds at 30 FPS
                    await manager.send_ping(self.stream_id)
            
            capture.release()
            
        print(f"Handler for '{self.stream_id}' has been stopped.")

    def start(self) -> bool:
        # Check if the handler is already running to prevent starting multiple threads
        if self.is_running():
            print("Handler is already running.")
            return False

        # Resets the stop flag to "False", allowing the while loops in "_process_stream" to run
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
        # Check if the handler is actually running before trying to stop it
        if not self.is_running():
            print("Handler is not running.")
            return False

        # Sets the internal flag to True, telling the while loops in "_process_stream" to terminate
        self._stop_event.set()
        self._thread.join(timeout=5)
        
        # Double checks to see if the thread is alive. If alive, its stuck
        if self._thread.is_alive():
            print("Error: Handler thread did not stop in time.")
            return False
        
        print(f"Stream handler for '{self.stream_id}' stopped successfully.")
        return True

    # A helper method to check if the thread is active
    def is_running(self) -> bool:
        return self._thread and self._thread.is_alive()

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