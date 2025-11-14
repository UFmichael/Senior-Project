import cv2
import threading
import time
import asyncio
from .combined_model import CombinedDetectionModel
import numpy as np
from .websocket_manager import manager

class StreamHandler:
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

    # This is the main function that runs continuously in the background thread
    async def _process_stream(self):
        print(f"Handler for '{self.stream_id}' starting: trying to connect to {self.stream_url}")
        
        # Frame skipping and timing control with adaptive frame rate
        frame_count = 0
        detection_frame_interval = 5  # Process YOLO every 5th frame
        display_frame_interval = 2    # Send to frontend (starts at ~15 FPS from 30 FPS source)
        last_detections = []  # Cache last detection results
        
        # Adaptive frame rate parameters
        min_display_interval = 1  # Max 30 FPS
        max_display_interval = 6  # Min 5 FPS
        last_adaptation_time = time.time()
        adaptation_interval = 3  # Adjust every 3 seconds
        
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
                if frame_count % detection_frame_interval == 0:
                    try:
                        is_success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if not is_success:
                            continue
                            
                        image_bytes = buffer.tobytes()
                        results = await self.model.predict(image_bytes)
                        
                        # Update cached detections - combine weapons and faces
                        last_detections = []
                        current_time = time.time()
                        should_print_alert = (current_time - self.last_alert_time) >= self.alert_cooldown
                        
                        # Process weapon detections
                        weapon_detections = results.get("weapon_detections", [])
                        for detection in weapon_detections:
                            if detection["confidence"] > 0.65:
                                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                                
                                # Only print alert if cooldown period has passed
                                if should_print_alert:
                                    print(f"🔴 WEAPON ALERT [{self.stream_id} @ {timestamp}]: "
                                          f"Detected {detection.get('original_class', 'weapon')} "
                                          f"with confidence {detection['confidence']:.2f}")
                                
                                last_detections.append({
                                    "type": "weapon",
                                    "class": detection.get("original_class", "weapon"),
                                    "confidence": float(detection["confidence"]),
                                    "bbox": detection.get("bbox", []),
                                    "timestamp": timestamp
                                })
                        
                        # Process face detections with emotions
                        face_detections = results.get("face_detections", [])
                        for face in face_detections:
                            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                            emotion = face.get("dominant_emotion", "unknown")
                            
                            # Only print alert if cooldown period has passed
                            if should_print_alert:
                                emotion_scores = face.get("emotion_scores", {})
                                emotion_conf = emotion_scores.get(emotion, 0) if emotion_scores else 0
                                print(f"FACE DETECTED [{self.stream_id} @ {timestamp}]: "
                                      f"Emotion: {emotion} ({emotion_conf:.0f}%)")
                            
                            last_detections.append({
                                "type": "face",
                                "emotion": emotion,
                                "emotion_scores": face.get("emotion_scores", {}),
                                "confidence": float(face.get("confidence", 0.0)),
                                "bbox": face.get("bbox", []),
                                "timestamp": timestamp
                            })
                        
                        # Update last alert time if we printed anything
                        if should_print_alert and (weapon_detections or face_detections):
                            self.last_alert_time = current_time
                    
                    except Exception as e:
                        print(f"[{self.stream_id}] Error processing frame: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Adaptive frame rate adjustment based on client performance
                current_time = time.time()
                if current_time - last_adaptation_time >= adaptation_interval:
                    slow_ratio = manager.get_slow_client_ratio(self.stream_id)
                    
                    if slow_ratio > 0.5:  # More than 50% of clients are slow
                        # Decrease frame rate (increase interval)
                        display_frame_interval = min(display_frame_interval + 1, max_display_interval)
                        print(f"[{self.stream_id}] Decreased frame rate due to slow clients ({slow_ratio:.1%}). New interval: {display_frame_interval}")
                    elif slow_ratio < 0.2 and display_frame_interval > min_display_interval:
                        # Increase frame rate (decrease interval) if clients are keeping up
                        display_frame_interval = max(display_frame_interval - 1, min_display_interval)
                        print(f"[{self.stream_id}] Increased frame rate. New interval: {display_frame_interval}")
                    
                    last_adaptation_time = current_time
                
                # Send frame to WebSocket clients only every display_frame_interval frames
                # and only if there are active connections
                if frame_count % display_frame_interval == 0 and manager.has_connections(self.stream_id):
                    try:
                        # Create annotated frame with bounding boxes
                        annotated_frame = frame.copy()
                        
                        for detection in last_detections:
                            if "bbox" in detection and detection["bbox"]:
                                bbox = detection["bbox"]
                                x1, y1, x2, y2 = map(int, bbox)
                                
                                detection_type = detection.get("type", "unknown")
                                
                                if detection_type == "weapon":
                                    # RED for weapons
                                    color = (0, 0, 255)
                                    label = f"{detection.get('class', 'weapon')}: {detection['confidence']:.2f}"
                                elif detection_type == "face":
                                    # BLUE for faces with emotion
                                    color = (255, 0, 0)
                                    emotion = detection.get('emotion', 'unknown')
                                    label = f"{emotion}"
                                else:
                                    # GREEN for other detections
                                    color = (0, 255, 0)
                                    label = f"{detection.get('class', 'unknown')}: {detection['confidence']:.2f}"
                                
                                # Draw rectangle
                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                                
                                # Add label background for better visibility
                                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                                cv2.rectangle(annotated_frame, 
                                            (x1, y1 - label_size[1] - 10), 
                                            (x1 + label_size[0], y1), 
                                            color, -1)
                                
                                # Add label text
                                cv2.putText(annotated_frame, label, (x1, y1 - 5),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        
                        # Encode with lower quality for faster transmission
                        is_success, encoded_frame = cv2.imencode(".jpg", annotated_frame, 
                                                                 [cv2.IMWRITE_JPEG_QUALITY, 60])
                        if is_success:
                            frame_bytes = encoded_frame.tobytes()
                            await manager.send_frame(
                                stream_id=self.stream_id,
                                frame_data=frame_bytes,
                                detections=last_detections
                            )
                    except Exception as e:
                        # Don't let WebSocket errors break the main processing loop
                        print(f"[{self.stream_id}] Error sending frame to WebSocket (non-critical): {e}")
                
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