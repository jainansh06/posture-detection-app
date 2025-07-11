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
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, origins=['https://posture-detection-app-dun.vercel.app'])


# Initialize MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)

def calculate_angle(point1, point2, point3):
    a = np.array(point1)
    b = np.array(point2)
    c = np.array(point3)
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc)) # cosine of angle using dot product 
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

@app.route("/")
def home():
    return "Flask backend is running correctly."


@app.route('/analyze_pose', methods=['POST']) #Main endpoint for analyzing posture from uploaded images
def analyze_pose():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']
        posture_type = request.form.get('posture_type')  # 'sitting' or 'squat'
        
        image = Image.open(file.stream)
        image_rgb = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        results = pose.process(cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB))
        if not results.pose_landmarks:
            return jsonify({'error': 'No pose detected'}), 400

        landmarks = results.pose_landmarks.landmark
        key_points = extract_key_points(landmarks)
        
        # Analyze based on specified posture type
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
            # If no posture type specified, use automatic detection (your existing logic)
            analysis = analyze_posture(key_points)

        return jsonify({
            'success': True,
            'landmarks_detected': True,
            'key_points': key_points,
            'analysis': analysis
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze_video', methods=['POST']) # Endpoint for analyzing posture from uploaded video files
def analyze_video():
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video provided'}), 400

        file = request.files['video']
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(video_path)

        results = process_video(video_path)

        os.remove(video_path)
        os.rmdir(temp_dir)

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_results = []
    frame_count = 0
    bad_posture_count = 0
    frame_skip = 5

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_skip == 0:
            results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                key_points = extract_key_points(landmarks)
                analysis = analyze_posture(key_points)
                frame_result = {
                    'frame': frame_count,
                    'timestamp': frame_count / 30.0,
                    'analysis': analysis
                }
                frame_results.append(frame_result)
                if analysis['overall_posture'] == 'bad':
                    bad_posture_count += 1

        frame_count += 1

    cap.release()

    total_analyzed_frames = len(frame_results)
    bad_posture_percentage = (bad_posture_count / total_analyzed_frames * 100) if total_analyzed_frames > 0 else 0

    return { #analysis results
        'success': True,
        'total_frames': frame_count,
        'analyzed_frames': total_analyzed_frames,
        'bad_posture_frames': bad_posture_count,
        'bad_posture_percentage': bad_posture_percentage,
        'frame_results': frame_results[-10:],
        'summary': {
            'overall_rating': 'good' if bad_posture_percentage < 30 else 'bad',
            'main_issues': get_main_issues(frame_results)
        }
    }

def get_main_issues(frame_results): #Analyze frame results to identify the most common posture problems
    issues = {}
    for frame in frame_results:
        sitting_problems = frame['analysis']['sitting_analysis'].get('problems', [])
        squat_problems = frame['analysis']['squat_analysis'].get('problems', [])
        for problem in sitting_problems + squat_problems:
            issues[problem] = issues.get(problem, 0) + 1
    return sorted(issues.items(), key=lambda x: x[1], reverse=True)[:3]

def extract_key_points(landmarks): # Extract key points needed for posture analysis.
    key_points = {}
    landmark_indices = { #correspond to specific body parts in MediaPipe's pose model
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

def analyze_posture(key_points): #posture analysis for both sitting and squat positions
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

@app.route('/health', methods=['GET'])
def health_check(): #Health check endpoint for monitoring and deployment verification
    return jsonify({'status': 'healthy'})

#if __name__ == '__main__':    aws
    #app.run(debug=True, host='0.0.0.0', port=5000)  aws
if __name__ == '__main__':
    # Use PORT environment variable provided by Render
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

