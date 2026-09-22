import cv2
import numpy as np
import time


class CameraManager:

    def __init__(self):

        # ================================================
        # CAMERA CONFIGURATION
        # ================================================

        self.simulation = False
        self.camera = None
        self.connected = False

    # ================================================
    # START CAMERA
    # ================================================

    def start(self):

        if self.simulation:

            print("Camera: Simulation mode")
            return

        # MacBook camera
        self.camera = cv2.VideoCapture(
            0,
            cv2.CAP_AVFOUNDATION
        )

        if not self.camera.isOpened():

            print("Camera: Failed to connect")
            print("Camera: Switching to simulation mode")

            self.simulation = True
            self.connected = False

            return

        self.connected = True

        print("Camera: Connected")

    # ================================================
    # GET CAMERA FRAME
    # ================================================

    def get_frame(self):

        # ============================================
        # SIMULATION MODE
        # ============================================

        if self.simulation:

            frame = np.zeros(
                (480, 640, 3),
                dtype=np.uint8
            )

            cv2.putText(
                frame,
                "SPIKY NEURON ROBOT",
                (150, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "CAMERA SIMULATION",
                (175, 230),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (200, 200, 200),
                2
            )

            cv2.putText(
                frame,
                time.strftime("%H:%M:%S"),
                (260, 280),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

        # ============================================
        # REAL CAMERA
        # ============================================

        else:

            if self.camera is None:

                return None

            success, frame = self.camera.read()

            if not success:

                print("Camera: Failed to read frame")

                return None

        # ============================================
        # JPEG ENCODING
        # ============================================

        success, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        if not success:

            return None

        return buffer.tobytes()

    # ================================================
    # CAMERA STATUS
    # ================================================

    def is_connected(self):

        return self.connected

    # ================================================
    # STOP CAMERA
    # ================================================

    def stop(self):

        if self.camera is not None:

            self.camera.release()

            self.camera = None

            self.connected = False

            print("Camera: Disconnected")


# ====================================================
# DIRECT TEST
# ====================================================

if __name__ == "__main__":

    camera = CameraManager()

    camera.start()

    frame = camera.get_frame()

    if frame is not None:

        print(
            "Camera frame received:",
            len(frame),
            "bytes"
        )

    else:

        print("Camera frame not received")

    camera.stop()