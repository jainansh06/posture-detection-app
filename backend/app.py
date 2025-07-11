
from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import tempfile
import os
import gc
from PIL import Image

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
    try:
        with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
            image_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                nose = [landmarks[mp_pose.PoseLandmark.NOSE.value].x,
                        landmarks[mp_pose.PoseLandmark.NOSE.value].y]
                left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                 landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                
                neck_angle = np.abs(left_shoulder[1] - nose[1]) * 180
                bad_posture = neck_angle > 20
                
                results_dict['analysis'] = {
                    'bad_posture': bad_posture,
                    'neck_angle': neck_angle,
                    'problems': [f'Neck bent too far: {neck_angle:.2f} degrees'] if bad_posture else []
                }
                results_dict['key_points'] = {
                    'nose': nose,
                    'left_shoulder': left_shoulder
                }
                results_dict['landmarks_detected'] = True
                results_dict['success'] = True
            else:
                results_dict['analysis'] = {'bad_posture': False, 'problems': []}
                results_dict['success'] = True
    except Exception as e:
        print(f"[ERROR] analyze_posture: {str(e)}")
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

    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
            file.save(tmp_name)
            print(f"[DEBUG] Saved file at {tmp_name}")
            image = cv2.imread(tmp_name)
            if image is None:
                print("[ERROR] cv2.imread returned None")
                return jsonify({'error': 'Failed to load image with cv2.imread'}), 400
            results = analyze_posture(image, posture_type)
            print(f"[DEBUG] Analysis Results: {results}")
            return jsonify(results)
    except Exception as e:
        print(f"[ERROR] /analyze_pose: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False, threaded=True)

