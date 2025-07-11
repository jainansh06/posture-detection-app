from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image
import io
import os
import gc
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, origins="*")

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    min_detection_confidence=0.5,
    model_complexity=0
)

@app.route("/")
def home():
    return jsonify({"message": "Flask backend running on Render.", "status": "healthy"})

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})

@app.route("/test", methods=["GET"])
def test():
    return jsonify({"message": "Test endpoint working", "mediapipe_available": True})

@app.route("/analyze_pose", methods=["POST"])
def analyze_pose():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image provided"}), 400

        file = request.files['image']
        posture_type = request.form.get('posture_type', 'sitting')

        image = Image.open(file.stream).convert('RGB')
        image_np = np.array(image)

        image_rgb = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        results = pose.process(cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB))

        if not results.pose_landmarks:
            return jsonify({"error": "No pose detected"}), 400

        landmarks = results.pose_landmarks.landmark
        key_points = extract_key_points(landmarks)

        # Analyze posture
        if posture_type == 'sitting':
            analysis = analyze_sitting(key_points)
        elif posture_type == 'squat':
            analysis = analyze_squat(key_points)
        else:
            analysis = analyze_posture(key_points)

        # Ensure 'overall_posture' is always present
        if 'overall_posture' not in analysis:
            analysis['overall_posture'] = 'bad' if analysis.get('bad_posture', False) else 'good'

        # Memory cleanup
        del image, image_np, image_rgb, results
        gc.collect()

        return jsonify({
            "success": True,
            "landmarks_detected": True,
            "key_points": key_points,
            "analysis": analysis
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_key_points(landmarks):
    key_points = {}
    indices = {
        "nose": 0,
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_hip": 23,
        "right_hip": 24,
        "left_knee": 25,
        "right_knee": 26,
        "left_ankle": 27,
        "right_ankle": 28
    }
    for name, idx in indices.items():
        lm = landmarks[idx]
        key_points[name] = {
            "x": lm.x,
            "y": lm.y,
            "z": lm.z,
            "visibility": lm.visibility
        }
    return key_points

def analyze_sitting(key_points):
    issues = {"bad_posture": False, "problems": []}
    try:
        nose = [key_points["nose"]["x"], key_points["nose"]["y"]]
        shoulder = [key_points["left_shoulder"]["x"], key_points["left_shoulder"]["y"]]
        hip = [key_points["left_hip"]["x"], key_points["left_hip"]["y"]]
        neck_angle = calculate_angle(nose, shoulder, hip)

        if neck_angle > 30:
            issues["bad_posture"] = True
            issues["problems"].append(f"Neck bent too much: {neck_angle:.1f}°")

        issues["neck_angle"] = neck_angle

    except Exception as e:
        issues["error"] = str(e)

    return issues

def analyze_squat(key_points):
    issues = {"bad_posture": False, "problems": []}
    try:
        knee_x = key_points["left_knee"]["x"]
        ankle_x = key_points["left_ankle"]["x"]
        if knee_x > ankle_x + 0.05:
            issues["bad_posture"] = True
            issues["problems"].append("Left knee over toe")

        shoulder = [key_points["left_shoulder"]["x"], key_points["left_shoulder"]["y"]]
        hip = [key_points["left_hip"]["x"], key_points["left_hip"]["y"]]
        knee = [key_points["left_knee"]["x"], key_points["left_knee"]["y"]]
        back_angle = calculate_angle(shoulder, hip, knee)

        if back_angle < 150:
            issues["bad_posture"] = True
            issues["problems"].append(f"Back angle too acute: {back_angle:.1f}°")

        issues["back_angle"] = back_angle

    except Exception as e:
        issues["error"] = str(e)

    return issues

def analyze_posture(key_points):
    sitting_analysis = analyze_sitting(key_points)
    squat_analysis = analyze_squat(key_points)
    issues = {
        "sitting_analysis": sitting_analysis,
        "squat_analysis": squat_analysis,
    }
    issues["bad_posture"] = sitting_analysis.get("bad_posture") or squat_analysis.get("bad_posture")
    issues["overall_posture"] = "bad" if issues["bad_posture"] else "good"
    return issues

def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    ba = a - b
    bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(np.clip(cosine, -1.0, 1.0))
    return np.degrees(angle)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
