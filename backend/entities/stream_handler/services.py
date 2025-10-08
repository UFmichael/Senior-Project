import cv2
import threading
import time
import asyncio
from entities.yolo.model import YOLOModel
import numpy as np

class StreamHandler:
    def __init__(self, stream_url: str):
        # Stores the RTMP stream URL that this handler will connect to
        self.stream_url = stream_url
        self._thread = None
        # A threading.Event object that acts as a safe flag to signal the thread when to stop
        self._stop_event = threading.Event()
        self.model = YOLOModel()

    # This is the main function that runs continuously in the background thread
    async def _process_stream(self):
        print(f"Handler starting: trying to connect to {self.stream_url}")
        
        # This is the outer reconnection loop, keeps running as long as the stop event isn't set
        while not self._stop_event.is_set():
            capture = cv2.VideoCapture(self.stream_url)
            
            # If the connection fails, wait 5 seconds to try reconnecting
            if not capture.isOpened():
                print("Error: Stream not available. Retrying in 5 seconds...")
                time.sleep(5)
                continue

            print("Handler connected to stream successfully!")

            # Runs when stream is connected, reads one single frame from the video stream at a time
            # Something we need to consider is if we want to read every single frame or skip frames
            # TODO: Implement frame skipping logic if needed to reduce load
            
            while not self._stop_event.is_set():
                was_successful, frame = capture.read()
                
                # Runs if the stream has been lost or has ended.
                if not was_successful:
                    print("Stream lost. Attempting to reconnect...")
                    break
                
                is_success, buffer = cv2.imencode(".jpg", frame)
                if not is_success:
                    print("Failed to encode frame")
                    continue
                
                # Process frame with YOLO model
                image_bytes = buffer.tobytes()
                try:
                    results = await self.model.predict(image_bytes)
                    
                    if results["detections"]:
                        for detection in results["detections"]:
                            if detection["confidence"] > 0.5:  # Confidence threshold
                                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                                print(f"ALERT [{timestamp}]: Detected {detection['class']} with confidence {detection['confidence']:.2f}")
                                
                                #TODO: Save detection details to a database, send notis to frontend, save the frame as an image file, etc.
                
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    import traceback
                    traceback.print_exc()
            
            capture.release()
            
        print("Stream handler has been stopped.")

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

        print("Stream handler started.")
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
        
        print("Stream handler stopped successfully.")
        return True

    # A helper method to check if the thread is active
    def is_running(self) -> bool:
        return self._thread and self._thread.is_alive()

# For now, we only use one stream but that will change in the future.
main_stream_handler = StreamHandler(stream_url="rtmp://127.0.0.1:1935/live/mystream")