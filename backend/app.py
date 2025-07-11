from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import tempfile
import os
import gc

app = Flask(__name__)
CORS(app)

mp_pose = mp.solutions.pose

@app.route('/')
def home():
    return "Posture Detection Backend Running"

def calculate_angle(a, b, c):
    """Calculate angle between three points"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def analyze_sitting_posture(landmarks):
    """Analyze sitting posture"""
    problems = []
    
    # Get key points
    nose = [landmarks[mp_pose.PoseLandmark.NOSE].x, landmarks[mp_pose.PoseLandmark.NOSE].y]
    left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y]
    right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y]
    left_ear = [landmarks[mp_pose.PoseLandmark.LEFT_EAR].x, landmarks[mp_pose.PoseLandmark.LEFT_EAR].y]
    right_ear = [landmarks[mp_pose.PoseLandmark.RIGHT_EAR].x, landmarks[mp_pose.PoseLandmark.RIGHT_EAR].y]
    left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP].y]
    right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP].y]
    
    # Calculate midpoints
    shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, (left_shoulder[1] + right_shoulder[1]) / 2]
    ear_mid = [(left_ear[0] + right_ear[0]) / 2, (left_ear[1] + right_ear[1]) / 2]
    hip_mid = [(left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2]
    
    # Check for problems
    if ear_mid[0] < shoulder_mid[0] - 0.05:
        problems.append("Forward head posture detected")
    
    shoulder_height_diff = abs(left_shoulder[1] - right_shoulder[1])
    if shoulder_height_diff > 0.03:
        problems.append("Uneven shoulder height")
    
    if shoulder_mid[0] < hip_mid[0] - 0.08:
        problems.append("Slouching posture detected")
    
    ear_height_diff = abs(left_ear[1] - right_ear[1])
    if ear_height_diff > 0.02:
        problems.append("Head tilt detected")
    
    bad_posture = len(problems) > 0
    
    return {
        'bad_posture': bad_posture,
        'problems': problems
    }

def analyze_squat_posture(landmarks):
    """Analyze squat posture"""
    problems = []
    
    # Get key points
    left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP].y]
    right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP].y]
    left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y]
    right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE].y]
    left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y]
    right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE].y]
    
    # Calculate angles
    left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
    right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
    avg_knee_angle = (left_knee_angle + right_knee_angle) / 2
    
    # Check for problems
    if avg_knee_angle > 120:
        problems.append("Squat too shallow - go deeper")
    elif avg_knee_angle < 70:
        problems.append("Squat too deep")
    
    knee_distance = abs(left_knee[0] - right_knee[0])
    hip_distance = abs(left_hip[0] - right_hip[0])
    if knee_distance < hip_distance * 0.8:
        problems.append("Knees caving inward")
    
    bad_posture = len(problems) > 0
    
    return {
        'bad_posture': bad_posture,
        'problems': problems,
        'knee_angle': avg_knee_angle
    }

def analyze_posture(image_np, posture_type='sitting'):
    """Main posture analysis function"""
    results_dict = {
        'analysis': {},
        'landmarks_detected': False,
        'success': False
    }

    try:
        with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
            image_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark

                if posture_type == 'sitting':
                    analysis = analyze_sitting_posture(landmarks)
                elif posture_type == 'squat':
                    analysis = analyze_squat_posture(landmarks)
                else:
                    analysis = analyze_sitting_posture(landmarks)

                results_dict['analysis'] = analysis
                results_dict['landmarks_detected'] = True
                results_dict['success'] = True
                
            else:
                results_dict['analysis'] = {
                    'bad_posture': False,
                    'problems': ['No person detected in image']
                }
                results_dict['success'] = True

    except Exception as e:
        results_dict['error'] = str(e)
        results_dict['success'] = False

    return results_dict

@app.route('/analyze_pose', methods=['POST'])
def analyze_pose():
    """Analyze pose from uploaded image"""
    posture_type = request.form.get('posture_type', 'sitting')
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    tmp_path = None
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
            
        # Read and analyze image
        image = cv2.imread(tmp_path)
        if image is None:
            return jsonify({'error': 'Could not read image file'}), 400

        results = analyze_posture(image, posture_type=posture_type)
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.route('/analyze_video', methods=['POST'])
def analyze_video():
    """Analyze posture from uploaded video"""
    posture_type = request.form.get('posture_type', 'sitting')
    
    if 'video' not in request.files:
        return jsonify({'error': 'No video uploaded'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    tmp_path = None
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
            
        # Process video
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return jsonify({'error': 'Could not read video file'}), 400
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        bad_posture_count = 0
        analyzed_frames = 0
        all_problems = []
        
        # Analyze every 30th frame
        frame_skip = 30
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_skip == 0:
                result = analyze_posture(frame, posture_type=posture_type)
                
                if result['success'] and result['landmarks_detected']:
                    analyzed_frames += 1
                    
                    if result['analysis']['bad_posture']:
                        bad_posture_count += 1
                        all_problems.extend(result['analysis']['problems'])
            
            frame_count += 1
        
        cap.release()
        
        # Calculate results
        bad_posture_percentage = (bad_posture_count / analyzed_frames * 100) if analyzed_frames > 0 else 0
        
        # Count most common problems
        problem_counts = {}
        for problem in all_problems:
            problem_counts[problem] = problem_counts.get(problem, 0) + 1
        
        main_issues = sorted(problem_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        overall_rating = 'Good' if bad_posture_percentage < 30 else 'Needs Improvement'
        
        results = {
            'total_frames': total_frames,
            'analyzed_frames': analyzed_frames,
            'bad_posture_percentage': round(bad_posture_percentage, 1),
            'summary': {
                'overall_rating': overall_rating,
                'main_issues': main_issues
            }
        }
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
