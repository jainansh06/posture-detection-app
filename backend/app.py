from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image
import io
import base64
import tempfile
import os
import gc
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, origins="*")  # Temporarily allow all origins

# Initialize MediaPipe with optimized settings
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(
    static_image_mode=True, 
    min_detection_confidence=0.5,
    model_complexity=0  # Use lighter model
)

@app.route("/")
def home():
    return jsonify({"message": "Flask backend is running correctly on Render.", "status": "healthy"})

@app.route("/test")
def test():
    return jsonify({"message": "Test endpoint working", "mediapipe_available": True})

@app.route('/analyze_pose', methods=['POST'])
def analyze_pose():
    try:
        # Add detailed logging
        print("Received request to analyze_pose")
        
        if 'image' not in request.files:
            print("No image in request")
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']
        posture_type = request.form.get('posture_type')
        
        print(f"Processing image, posture_type: {posture_type}")
        
        # Process image with error handling
        try:
            image = Image.open(file.stream)
            image_array = np.array(image)
            
            # Convert to RGB if necessary
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                image_rgb = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            else:
                image_rgb = image_array
                
            print("Image loaded successfully")
            
        except Exception as img_error:
            print(f"Image processing error: {img_error}")
            return jsonify({'error': f'Image processing failed: {str(img_error)}'}), 400

        # Process with MediaPipe
        try:
            results = pose.process(cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB))
            print(f"MediaPipe processing complete. Landmarks detected: {results.pose_landmarks is not None}")
            
            if not results.pose_landmarks:
                return jsonify({'error': 'No pose detected'}), 400

            landmarks = results.pose_landmarks.landmark
            key_points = extract_key_points(landmarks)
            
            # Analyze based on posture type
            if posture_type == 'sitting':
                sitting_analysis = analyze_sitting(key_points)
                analysis = {
                    'overall_posture': 'bad' if sitting_analysis.get('bad_posture', False) else 'good',
                    'sitting_analysis': sitting_analysis
                }
            elif posture_type == 'squat':
                squat_analysis = analyze_squat(key_points)
                analysis = {
                    'overall_posture': 'bad' if squat_analysis.get('bad_posture', False) else 'good',
                    'squat_analysis': squat_analysis
                }
            else:
                analysis = analyze_posture(key_points)

            print("Analysis complete")
            
            # Clean up memory
            del image, image_array, image_rgb, results
            gc.collect()
            
            return jsonify({
                'success': True,
                'landmarks_detected': True,
                'key_points': key_points,
                'analysis': analysis
            })
            
        except Exception as pose_error:
            print(f"Pose processing error: {pose_error}")
            return jsonify({'error': f'Pose processing failed: {str(pose_error)}'}), 500

    except Exception as e:
        print(f"General error: {e}")
        return jsonify({'error': str(e)}), 500

def extract_key_points(landmarks):
    key_points = {}
    landmark_indices = {
        'nose': 0,
        'left_shoulder': 11,
        'right_shoulder': 12,
        'left_hip': 23,
        'right_hip': 24,
        'left_knee': 25,
        'right_knee': 26,
        'left_ankle': 27,
        'right_ankle': 28
    }
    for name, idx in landmark_indices.items():
        landmark = landmarks[idx]
        key_points[name] = {
            'x': landmark.x,
            'y': landmark.y,
            'z': landmark.z,
            'visibility': landmark.visibility
        }
    return key_points

def analyze_posture(key_points):
    analysis = {
        'squat_analysis': {},
        'sitting_analysis': {},
        'overall_posture': 'good'
    }
    squat_issues = {'bad_posture': False, 'problems': []}
    sitting_issues = {'bad_posture': False, 'problems': []}

    if check_squat_position(key_points):
        squat_issues = analyze_squat(key_points)

    sitting_issues = analyze_sitting(key_points)

    analysis['squat_analysis'] = squat_issues
    analysis['sitting_analysis'] = sitting_issues

    if squat_issues.get('bad_posture', False) or sitting_issues.get('bad_posture', False):
        analysis['overall_posture'] = 'bad'

    return analysis

def check_squat_position(key_points):
    left_knee_y = key_points['left_knee']['y']
    left_hip_y = key_points['left_hip']['y']
    return (left_knee_y - left_hip_y) > 0.1

def analyze_squat(key_points):
    issues = {'bad_posture': False, 'problems': []}
    try:
        left_knee_x = key_points['left_knee']['x']
        left_ankle_x = key_points['left_ankle']['x']
        if left_knee_x > left_ankle_x + 0.05:
            issues['bad_posture'] = True
            issues['problems'].append('Left knee over toe')

        shoulder_point = [key_points['left_shoulder']['x'], key_points['left_shoulder']['y']]
        hip_point = [key_points['left_hip']['x'], key_points['left_hip']['y']]
        knee_point = [key_points['left_knee']['x'], key_points['left_knee']['y']]
        back_angle = calculate_angle(shoulder_point, hip_point, knee_point)

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
        nose_point = [key_points['nose']['x'], key_points['nose']['y']]
        shoulder_point = [key_points['left_shoulder']['x'], key_points['left_shoulder']['y']]
        hip_point = [key_points['left_hip']['x'], key_points['left_hip']['y']]
        neck_angle = calculate_angle(nose_point, shoulder_point, hip_point)

        if neck_angle > 30:
            issues['bad_posture'] = True
            issues['problems'].append(f'Neck bent too much: {neck_angle:.1f}°')
        issues['neck_angle'] = neck_angle

    except Exception as e:
        issues['error'] = str(e)

    return issues

def calculate_angle(point1, point2, point3):
    a = np.array(point1)
    b = np.array(point2)
    c = np.array(point3)
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
