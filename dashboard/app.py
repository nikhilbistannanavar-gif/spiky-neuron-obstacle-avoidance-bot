from flask import Flask, render_template, jsonify, Response
from flask_cors import CORS

from camera.camera_manager import CameraManager

from sensors.sensor_manager import get_sensor_data
from snn.navigation_network import NavigationSNN
from robot.motor_controller import MotorController

import threading
import time
import webbrowser


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)
CORS(app)


# ============================================================
# ROBOT COMPONENTS
# ============================================================

snn = NavigationSNN()

motor_controller = MotorController()

camera = CameraManager()
camera.start()


# ============================================================
# EMERGENCY STOP STATE
# ============================================================

emergency_stop_active = False

state_lock = threading.Lock()


# ============================================================
# CURRENT ROBOT STATE
# ============================================================

robot_state = {

    "sensors": {

        "left": 0,
        "front": 0,
        "right": 0,

        "roll": 0,
        "pitch": 0,
        "yaw": 0,

        "temperature": None,
        "gas": None
    },


    "snn": {

        "activity": {

            "FORWARD": 0,
            "LEFT": 0,
            "RIGHT": 0,
            "STOP": 0
        },

        "decision": "STOP"
    },


    "motors": {

        "left": 0,
        "right": 0
    },


    "system": {

        "emergency_stop": False,

        "control_loop": True,

        "status": "AUTONOMOUS"
    }

}


# ============================================================
# SAFE MOTOR STOP
# ============================================================

def force_motor_stop():

    try:

        motor_controller.stop()

    except Exception as error:

        print("Motor stop error:", error)


    robot_state["motors"]["left"] = 0
    robot_state["motors"]["right"] = 0


# ============================================================
# ROBOT CONTROL LOOP
# ============================================================

def robot_control_loop():

    global emergency_stop_active


    print("ROBOT CONTROL LOOP")
    print("Press Ctrl+C to stop.")
    print("=" * 50)


    while True:

        try:

            # ==================================================
            # READ SENSOR DATA
            # ==================================================

            sensor_data = get_sensor_data()


            left = sensor_data["left"]

            front = sensor_data["front"]

            right = sensor_data["right"]


            # ==================================================
            # UPDATE SENSOR STATE
            # ==================================================

            robot_state["sensors"].update(
                sensor_data
            )


            # ==================================================
            # CHECK EMERGENCY STOP
            # ==================================================

            with state_lock:

                estop = emergency_stop_active


            if estop:

                # Emergency stop has absolute priority.

                force_motor_stop()


                robot_state["snn"]["decision"] = \
                    "EMERGENCY STOP"


                robot_state["system"]["emergency_stop"] = \
                    True


                robot_state["system"]["status"] = \
                    "EMERGENCY STOP"


                time.sleep(0.1)

                continue


            # ==================================================
            # SNN NAVIGATION DECISION
            # ==================================================

            action, activity = snn.decide(

                left,
                front,
                right

            )


            # ==================================================
            # EXECUTE MOTOR COMMAND
            # ==================================================

            motor_controller.execute(
                action
            )


            # ==================================================
            # UPDATE MOTOR STATE
            # ==================================================

            motor_values = \
                motor_controller.get_motor_state()


            robot_state["motors"]["left"] = \
                motor_values["left"]


            robot_state["motors"]["right"] = \
                motor_values["right"]


            # ==================================================
            # UPDATE SNN STATE
            # ==================================================

            robot_state["snn"]["activity"] = \
                activity


            robot_state["snn"]["decision"] = \
                action


            # ==================================================
            # UPDATE SYSTEM STATE
            # ==================================================

            robot_state["system"]["emergency_stop"] = \
                False


            robot_state["system"]["status"] = \
                "AUTONOMOUS"


            # ==================================================
            # CONTROL LOOP DELAY
            # ==================================================

            time.sleep(0.5)


        except Exception as error:

            print(
                "CONTROL LOOP ERROR:",
                error
            )


            # ==================================================
            # SAFETY FALLBACK
            # ==================================================

            force_motor_stop()


            robot_state["snn"]["decision"] = \
                "ERROR"


            robot_state["system"]["status"] = \
                "FAULT"


            time.sleep(1)


# ============================================================
# DASHBOARD PAGE
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# ROBOT STATUS API
# ============================================================

@app.route("/api/status")
def status():

    return jsonify(
        robot_state
    )


# ============================================================
# EMERGENCY STOP
# ============================================================

@app.route(
    "/api/emergency-stop",
    methods=["POST"]
)
def emergency_stop():

    global emergency_stop_active


    # ========================================================
    # ACTIVATE ESTOP
    # ========================================================

    with state_lock:

        emergency_stop_active = True


    # ========================================================
    # IMMEDIATE MOTOR STOP
    # ========================================================

    force_motor_stop()


    # ========================================================
    # UPDATE STATE
    # ========================================================

    robot_state["snn"]["decision"] = \
        "EMERGENCY STOP"


    robot_state["system"]["emergency_stop"] = \
        True


    robot_state["system"]["status"] = \
        "EMERGENCY STOP"


    print("=" * 50)

    print(
        "!!! EMERGENCY STOP ACTIVATED !!!"
    )

    print(
        "Motors forced to STOP"
    )

    print(
        "SNN commands are blocked"
    )

    print("=" * 50)


    return jsonify({

        "success": True,

        "emergency_stop": True,

        "message":
            "Emergency stop activated"

    })


# ============================================================
# RESET EMERGENCY STOP
# ============================================================

@app.route(
    "/api/reset-estop",
    methods=["POST"]
)
def reset_estop():

    global emergency_stop_active


    # ========================================================
    # RELEASE ESTOP
    # ========================================================

    with state_lock:

        emergency_stop_active = False


    # ========================================================
    # UPDATE STATE
    # ========================================================

    robot_state["system"]["emergency_stop"] = \
        False


    robot_state["system"]["status"] = \
        "AUTONOMOUS"


    robot_state["snn"]["decision"] = \
        "WAITING"


    print("=" * 50)

    print(
        "Emergency stop reset"
    )

    print(
        "Autonomous control ENABLED"
    )

    print("=" * 50)


    return jsonify({

        "success": True,

        "emergency_stop": False,

        "message":
            "Emergency stop reset"

    })


# ============================================================
# CAMERA VIDEO STREAM
# ============================================================

@app.route("/video_feed")
def video_feed():

    def generate():

        while True:

            frame = camera.get_frame()


            if frame is None:

                time.sleep(0.05)

                continue


            yield (

                b"--frame\r\n"

                b"Content-Type: image/jpeg\r\n\r\n"

                + frame

                + b"\r\n"

            )


            time.sleep(0.05)


    return Response(

        generate(),

        mimetype=
        "multipart/x-mixed-replace; boundary=frame"

    )


# ============================================================
# START ROBOT CONTROL THREAD
# ============================================================

control_thread = threading.Thread(

    target=robot_control_loop,

    daemon=True

)

control_thread.start()


# ============================================================
# START FLASK SERVER
# ============================================================

if __name__ == "__main__":

    webbrowser.open("http://127.0.0.1:5050")

    app.run(

        host="127.0.0.1",

        port=5050,

        debug=True,

        use_reloader=False

    )