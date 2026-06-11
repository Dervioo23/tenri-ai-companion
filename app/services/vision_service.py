import cv2
import time
import threading
import logging
from app.config import Config

logger = logging.getLogger("AICompanion.VisionService")

class VisionService:
    # Minimum seconds between debug snapshots while a face is visible.
    SNAPSHOT_INTERVAL_SECONDS = 15.0

    def __init__(self):
        self.enabled = Config.VISION_ENABLED
        self.camera_active = False
        self.cap = None
        self.thread = None
        self.running = False
        
        # State variables
        self.face_detected = False
        self.face_count = 0
        self.motion_detected = False

        # Snapshot throttle: write at most one frame per interval. Uses a
        # monotonic timestamp instead of `int(time.time()) % N` which fired on
        # every ~10 FPS iteration within the matching second (~10 writes). See BUG-08.
        self._last_snapshot_at = 0.0

        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Load Haar Cascade for face detection
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                logger.error("Failed to load Haar Cascade face classifier.")
                self.face_cascade = None
        except Exception as e:
            logger.error(f"Error loading Haar Cascade: {e}")
            self.face_cascade = None

    def start(self):
        """Starts the background thread for capturing video context."""
        if not self.enabled:
            logger.info("Vision service is disabled by configuration.")
            return

        if self.running:
            logger.info("Vision service thread already running.")
            return

        self.running = True
        self.thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.thread.start()
        logger.info("Vision background thread started.")

    def stop(self):
        """Stops the vision thread and releases camera."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        
        if self.cap:
            try:
                self.cap.release()
                logger.info("Webcam released.")
            except Exception as e:
                logger.error(f"Error releasing webcam: {e}")
            self.cap = None
        
        self.camera_active = False

    def _camera_loop(self):
        """Background loop for fetching camera frames and analyzing them."""
        # Try to open webcam (0 is default)
        try:
            # On Windows, cv2.CAP_DSHOW can speed up startup significantly
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                # Fallback without CAP_DSHOW
                self.cap = cv2.VideoCapture(0)
                
            if not self.cap.isOpened():
                logger.warning("Could not open webcam index 0. Vision features will be disabled.")
                self.running = False
                return
                
            self.camera_active = True
            logger.info("Webcam initialized successfully.")
        except Exception as e:
            logger.error(f"Exception opening camera: {e}")
            self.running = False
            return

        prev_frame_gray = None
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    time.sleep(0.1)
                    continue

                # Resize for faster processing
                small_frame = cv2.resize(frame, (320, 240))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                gray_blurred = cv2.GaussianBlur(gray, (21, 21), 0)

                # Face Detection
                faces = []
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(
                        gray, 
                        scaleFactor=1.2, 
                        minNeighbors=4, 
                        minSize=(30, 30)
                    )

                # Motion Detection
                motion = False
                if prev_frame_gray is not None:
                    frame_delta = cv2.absdiff(prev_frame_gray, gray_blurred)
                    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                    thresh = cv2.dilate(thresh, None, iterations=2)
                    
                    # Calculate white pixel percentage to detect motion
                    height, width = thresh.shape
                    total_pixels = height * width
                    white_pixels = cv2.countNonZero(thresh)
                    ratio = white_pixels / total_pixels
                    
                    # If more than 1.5% of pixels changed, we classify as motion
                    if ratio > 0.015:
                        motion = True

                prev_frame_gray = gray_blurred

                # Update states under lock
                with self.lock:
                    self.face_detected = len(faces) > 0
                    self.face_count = len(faces)
                    self.motion_detected = motion
                    face_detected_now = self.face_detected

                # Save a debug snapshot when a face is present, throttled to at most
                # once every SNAPSHOT_INTERVAL_SECONDS so the ~10 FPS loop doesn't
                # flood disk with identical writes (BUG-08).
                if self._should_snapshot(face_detected_now, time.monotonic()):
                    snapshot_path = Config.SNAPSHOTS_DIR / "latest_face.jpg"
                    cv2.imwrite(str(snapshot_path), frame)
                    logger.debug(f"Saved camera snapshot to {snapshot_path}")

                # Sleep to maintain ~10 FPS and keep CPU usage low
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in vision thread loop: {e}")
                time.sleep(0.5)

    def _should_snapshot(self, face_detected: bool, now: float) -> bool:
        """Return True at most once per SNAPSHOT_INTERVAL_SECONDS while a face is
        visible. Records the snapshot time as a side effect when it returns True."""
        if not face_detected:
            return False
        if now - self._last_snapshot_at < self.SNAPSHOT_INTERVAL_SECONDS:
            return False
        self._last_snapshot_at = now
        return True

    def get_visual_context(self) -> dict:
        """Returns the current visual environment context safely."""
        if not self.enabled or not self.camera_active:
            return {"face_detected": False, "face_count": 0, "motion_detected": False}

        with self.lock:
            return {
                "face_detected": self.face_detected,
                "face_count": self.face_count,
                "motion_detected": self.motion_detected
            }
