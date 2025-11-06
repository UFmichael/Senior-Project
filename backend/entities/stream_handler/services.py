import cv2
import threading
import time
import asyncio
from entities.yolo.model import YOLOModel
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
        self.model = YOLOModel()

    # This is the main function that runs continuously in the background thread
    async def _process_stream(self):
        print(f"Handler for '{self.stream_id}' starting: trying to connect to {self.stream_url}")
        
        # Frame skipping and timing control
        frame_count = 0
        detection_frame_interval = 5  # Process YOLO every 5th frame
        display_frame_interval = 2    # Send to frontend every 2nd frame (15 FPS from 30 FPS source)
        last_detections = []  # Cache last detection results
        
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
                
                # Process frame with YOLO model only every Nth frame
                if frame_count % detection_frame_interval == 0:
                    try:
                        # Resize frame for faster YOLO processing (optional - trade accuracy for speed)
                        # Uncomment the next two lines if you want to process smaller frames
                        # detection_frame = cv2.resize(frame, (640, 480))
                        # is_success, buffer = cv2.imencode(".jpg", detection_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        
                        is_success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if not is_success:
                            continue
                            
                        image_bytes = buffer.tobytes()
                        results = await self.model.predict(image_bytes)
                        
                        # Update cached detections
                        last_detections = []
                        if results["detections"]:
                            for detection in results["detections"]:
                                if detection["confidence"] > 0.65:  # Increased threshold for better accuracy
                                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                                    print(f"ALERT [{self.stream_id} @ {timestamp}]: Detected {detection['class']} with confidence {detection['confidence']:.2f}")
                                    
                                    last_detections.append({
                                        "class": detection["class"],
                                        "confidence": float(detection["confidence"]),
                                        "bbox": detection.get("bbox", []),
                                        "timestamp": timestamp
                                    })
                    
                    except Exception as e:
                        print(f"[{self.stream_id}] Error processing frame: {e}")
                        import traceback
                        traceback.print_exc()
                
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
                                
                                # Draw rectangle
                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                
                                # Add label
                                label = f"{detection['class']}: {detection['confidence']:.2f}"
                                cv2.putText(annotated_frame, label, (x1, y1 - 10),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
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