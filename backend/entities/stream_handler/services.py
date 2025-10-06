# cv2 is the OpenCV library which is used for all video capturing and processing.
import cv2
import threading
import time

class StreamHandler:
    def __init__(self, stream_url: str):
        # Stores the RTMP stream URL ("rtmp://...") that this handler will connect to.
        self.stream_url = stream_url
        # A placeholder to hold the background thread object once it's created. Starts as None.
        self._thread = None
        # A threading.Event object that acts as a safe "flag" to signal the thread when to stop.
        self._stop_event = threading.Event()

    # This is the main function that runs continuously in the background thread.
    def _process_stream(self):
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
                
                # Proof backend is processing frames (remove later as it spams console).
                print(f"Processing frame with shape: {frame.shape}")
                
                # AI MODEL SHOULD GO HERE THIS IS PROCESSING FRAME BY FRAME.
            
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
        # Creates a new thread object. The tread will execute the "_process_stream" function.
        self._thread = threading.Thread(target=self._process_stream, daemon=True)
        # Starts the execution of the "_process_stream" method in the background.
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