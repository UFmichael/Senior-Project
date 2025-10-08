# cv2 is the OpenCV library which is used for all video capturing and processing.
import cv2
import threading
import time
import asyncio
from entities.yolo.model import YOLOModel
import numpy as np

class StreamHandler:
    def __init__(self, stream_url: str):
        # Stores the RTMP stream URL ("rtmp://...") that this handler will connect to.
        self.stream_url = stream_url
        # A placeholder to hold the background thread object once it's created. Starts as None.
        self._thread = None
        # A threading.Event object that acts as a safe "flag" to signal the thread when to stop.
        self._stop_event = threading.Event()
        # Initialize the YOLO model
        self.model = YOLOModel()

    # This is the main function that runs continuously in the background thread.
    async def _process_stream(self):
        print(f"Handler starting: trying to connect to {self.stream_url}")
        
        # This is the outer reconnection loop. It keeps running as long as the stop event isn't set.
        while not self._stop_event.is_set():
            capture = cv2.VideoCapture(self.stream_url)
            
            # If the connection fails, wait 5 seconds then continue to the next loop iteration to try reconnecting.
            if not capture.isOpened():
                print("Error: Stream not available. Retrying in 5 seconds...")
                time.sleep(5)
                continue

            print("Handler connected to stream successfully!")
            
            # Runs when stream is finally connected, reads one single frame from the video stream at a time.
            while not self._stop_event.is_set():
                # "was_successful" is True if a frame was read successfully, False otherwise.
                # "frame" is the actual image data of the frame.
                was_successful, frame = capture.read()
                
                # Runs if the stream has been lost or has ended.
                if not was_successful:
                    print("Stream lost. Attempting to reconnect...")
                    break
                
                # Convert frame to bytes for YOLO model
                is_success, buffer = cv2.imencode(".jpg", frame)
                if not is_success:
                    print("Failed to encode frame")
                    continue
                
                # Process frame with YOLO model
                image_bytes = buffer.tobytes()
                try:
                    # Need to use await here since predict is an async function
                    results = await self.model.predict(image_bytes)
                    
                    # Process detections
                    if results["detections"]:
                        for detection in results["detections"]:
                            if detection["confidence"] > 0.5:  # Confidence threshold
                                # Log detection with timestamp
                                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                                print(f"⚠️ ALERT [{timestamp}]: Detected {detection['class']} with confidence {detection['confidence']:.2f}")
                                
                                # Here you could add additional handling like:
                                # - Save detection details to a database
                                # - Send notifications
                                # - Save the frame as an image file
                                # - Trigger other security measures
                
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    import traceback
                    traceback.print_exc()  # Print full error traceback
            
            # Closes the connection with the stream.
            capture.release()
            
        print("Stream handler has been stopped.")

    # The public method to start the background process. Returns True if successful.
    def start(self) -> bool:
        # Check if the handler is already running to prevent starting multiple threads.
        if self.is_running():
            print("Handler is already running.")
            return False

        # Resets the stop flag to "False", allowing the while loops in "_process_stream" to run.
        self._stop_event.clear()
        
        # Create an event loop in the new thread
        async def run_async():
            await self._process_stream()
            
        def thread_target():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_async())
            loop.close()
        
        # Creates a new thread object with the async-aware target
        self._thread = threading.Thread(target=thread_target, daemon=True)
        # Starts the execution of the thread
        self._thread.start()

        print("Stream handler started.")
        return True

    # The public method to stop the background process. Returns True if successful.
    def stop(self) -> bool:
        # Check if the handler is actually running before trying to stop it.
        if not self.is_running():
            print("Handler is not running.")
            return False

        # Sets the internal flag to True, telling the while loops in "_process_stream" to terminate.
        self._stop_event.set()
        # The main program will wait here for the background thread to finish.
        self._thread.join(timeout=5)
        
        # Double checks to see if the thread is alive. If alive, its stuck.
        if self._thread.is_alive():
            print("Error: Handler thread did not stop in time.")
            return False
        
        print("Stream handler stopped successfully.")
        return True

    # A helper method to check if the thread is active.
    def is_running(self) -> bool:
        return self._thread and self._thread.is_alive()

# For now, we are using a singleton but in the future we will take multiple stream_urls
main_stream_handler = StreamHandler(stream_url="rtmp://127.0.0.1:1935/live/mystream")