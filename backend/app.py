from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import tempfile
import os
import gc

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://posture-detection-app-dun.vercel.app"}})

mp_pose = mp.solutions.pose

@app.route('/')
def home():
    return "Posture Detection Backend Running"

def analyze_posture(image_np, posture_type='sitting'):
    results_dict = {
        'analysis': {},
        'key_points': {},
        'landmarks_detected': False,
        'success': False
    }

    max_dim = 640
    if max(image_np.shape) > max_dim:
        scale = max_dim / max(image_np.shape)
        new_size = (int(image_np.shape[1] * scale), int(image_np.shape[0] * scale))
        image_np = cv2.resize(image_np, new_size, interpolation=cv2.INTER_AREA)

    try:
        with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
            image_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark

                left_shoulder = [float(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x),
                                 float(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y)]
                nose = [float(landmarks[mp_pose.PoseLandmark.NOSE].x),
                        float(landmarks[mp_pose.PoseLandmark.NOSE].y)]

                results_dict['key_points'] = {
                    'left_shoulder': left_shoulder,
                    'nose': nose
                }

                # Dummy logic for demonstration
                results_dict['analysis'] = {
                    'bad_posture': bool(False),
                    'neck_angle': float(10.88),
                    'problems': []
                }

                results_dict['landmarks_detected'] = True
                results_dict['success'] = True
            else:
                results_dict['analysis'] = {
                    'bad_posture': bool(False),
                    'problems': []
                }
                results_dict['success'] = True

    except Exception as e:
        results_dict['error'] = str(e)

    gc.collect()
    return results_dict

@app.route('/analyze_pose', methods=['POST'])
def analyze_pose():
    posture_type = request.form.get('posture_type', 'sitting')
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            image = cv2.imread(tmp.name)

        if image is None:
            return jsonify({'error': 'Failed to load image'}), 400

        results = analyze_posture(image, posture_type=posture_type)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if tmp and os.path.exists(tmp.name):
            os.remove(tmp.name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
