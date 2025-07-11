from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image
import io
import os
import gc

app = Flask(__name__)
CORS(app, origins="*")  # For testing; restrict in production

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

@app.route("/")
def home():
    return jsonify({"message": "Flask backend is running correctly on Render.", "status": "healthy"})

@app.route("/test")
def test():
    return jsonify({"message": "Test endpoint working", "mediapipe_available": True})

@app.route('/analyze_pose', methods=['POST'])
def analyze_pose():
    try:
        print("[INFO] Received request to /analyze_pose")

        if 'image' not in request.files:
            print("[WARN] No image provided")
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']
        posture_type = request.form.get('posture_type', 'general')

        try:
            image = Image.open(file.stream).convert('RGB')
            image = image.resize((320, 320))  # Memory-efficient resizing
            image_array = np.array(image)
            print("[INFO] Image loaded and resized successfully")

        except Exception as img_error:
            print(f"[ERROR] Image processing failed: {img_error}")
            return jsonify({'error': f'Image processing failed: {str(img_error)}'}), 400

        # Lazy initialization for memory efficiency
        pose = mp_pose.Pose(
            static_image_mode=True,
            min_detection_confidence=0.5,
            model_complexity=0  # Light model
        )

        try:
            results = pose.process(image_array)
            print(f"[INFO] MediaPipe processing done, landmarks detected: {results.pose_landmarks is not None}")

            if not results.pose_landmarks:
                pose.close()
                return jsonify({'error': 'No pose detected'}), 400

            landmarks = results.pose_landmarks.landmark
            key_points = extract_key_points(landmarks)

            # Analysis based on posture_type
            if posture_type == 'sitting':
                analysis = analyze_sitting(key_points)
            elif posture_type == 'squat':
                analysis = analyze_squat(key_points)
            else:
                analysis = analyze_posture(key_points)

            pose.close()  # Explicit cleanup
            gc.collect()  # Force garbage collection

            return jsonify({
                'success': True,
                'landmarks_detected': True,
                'key_points': key_points,
                'analysis': analysis
            })

        except Exception as pose_error:
            pose.close()
            print(f"[ERROR] Pose processing failed: {pose_error}")
            return jsonify({'error': f'Pose processing failed: {str(pose_error)}'}), 500

    except Exception as e:
        print(f"[ERROR] General error: {e}")
        return jsonify({'error': str(e)}), 500

def extract_key_points(landmarks):
    key_points = {}
    indices = {
        'nose': 0, 'left_shoulder': 11, 'right_shoulder': 12,
        'left_hip': 23, 'right_hip': 24,
        'left_knee': 25, 'right_knee': 26,
        'left_ankle': 27, 'right_ankle': 28
    }
    for name, idx in indices.items():
        lm = landmarks[idx]
        key_points[name] = {'x': lm.x, 'y': lm.y, 'z': lm.z, 'visibility': lm.visibility}
    return key_points

def analyze_posture(key_points):
    squat_analysis = analyze_squat(key_points)
    sitting_analysis = analyze_sitting(key_points)
    overall_posture = 'bad' if squat_analysis.get('bad_posture') or sitting_analysis.get('bad_posture') else 'good'
    return {
        'squat_analysis': squat_analysis,
        'sitting_analysis': sitting_analysis,
        'overall_posture': overall_posture
    }

def analyze_squat(key_points):
    issues = {'bad_posture': False, 'problems': []}
    try:
        left_knee_x = key_points['left_knee']['x']
        left_ankle_x = key_points['left_ankle']['x']
        if left_knee_x > left_ankle_x + 0.05:
            issues['bad_posture'] = True
            issues['problems'].append('Left knee over toe')

        shoulder = [key_points['left_shoulder']['x'], key_points['left_shoulder']['y']]
        hip = [key_points['left_hip']['x'], key_points['left_hip']['y']]
        knee = [key_points['left_knee']['x'], key_points['left_knee']['y']]
        back_angle = calculate_angle(shoulder, hip, knee)

        if back_angle < 150:
            issues['bad_posture'] = True
            issues['problems'].append(f'Back angle too acute: {back_angle:.1f}°')
        issues['back_angle'] = back_angle

    except Exception as e:
        issues['error'] = str(e)

    return issues

def analyze_sitting(key_points):
    issues = {'bad_posture': False, 'problems': []}
    try:
        nose = [key_points['nose']['x'], key_points['nose']['y']]
        shoulder = [key_points['left_shoulder']['x'], key_points['left_shoulder']['y']]
        hip = [key_points['left_hip']['x'], key_points['left_hip']['y']]
        neck_angle = calculate_angle(nose, shoulder, hip)

        if neck_angle > 30:
            issues['bad_posture'] = True
            issues['problems'].append(f'Neck bent too much: {neck_angle:.1f}°')
        issues['neck_angle'] = neck_angle

    except Exception as e:
        issues['error'] = str(e)

    return issues

def calculate_angle(p1, p2, p3):
    a, b, c = np.array(p1), np.array(p2), np.array(p3)
    ba = a - b
    bc = c - b
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
    return angle

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
