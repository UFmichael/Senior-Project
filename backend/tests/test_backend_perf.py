import cv2
import time
import asyncio

from entities.stream_handler.combined_model import CombinedDetectionModel

STREAM_URL = "rtmp://127.0.0.1:1935/live/1"


async def main():
    print("Opening stream...")

    cap = cv2.VideoCapture(STREAM_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("❌ Could NOT open RTMP stream.")
        return
    
    model = CombinedDetectionModel()

    print("Stream opened. Running FULL model (weapons + faces) with local display...\n")

    frame_count = 0
    start = time.time()

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Stream ended or lost.")
            break

        frame_count += 1

        # Encode to JPEG like in real pipeline
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            continue

        image_bytes = buf.tobytes()

        # 🔹 Run BOTH weapons + faces on this frame
        t0 = time.time()
        results = await model.predict(image_bytes, detect_faces=True)
        t1 = time.time()

        print(f"model.predict took {t1 - t0:.3f} seconds (faces=True)")

        # Draw bboxes for quick visual sanity check
        detections = []
        detections.extend(results.get("weapon_detections", []))
        detections.extend(results.get("face_detections", []))

        for det in detections:
            bbox = det.get("bbox", [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        # Show frame
        cv2.imshow("Backend model test (no WebSocket)", frame)

        now = time.time()
        if now - start >= 5:
            fps = frame_count / (now - start)
            print(f"🔥 Backend FPS (with weapons+faces, no frontend): {fps:.2f}")
            frame_count = 0
            start = now

        # Quit with 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(main())