from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import tempfile
import os
import gc
import math

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://posture-detection-app-dun.vercel.app"}})

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
    """Analyze sitting posture based on landmarks"""
    problems = []
    
    # Get key landmarks
    nose = [landmarks[mp_pose.PoseLandmark.NOSE].x, landmarks[mp_pose.PoseLandmark.NOSE].y]
    left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y]
    right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y]
    left_ear = [landmarks[mp_pose.PoseLandmark.LEFT_EAR].x, landmarks[mp_pose.PoseLandmark.LEFT_EAR].y]
    right_ear = [landmarks[mp_pose.PoseLandmark.RIGHT_EAR].x, landmarks[mp_pose.PoseLandmark.RIGHT_EAR].y]
    left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP].y]
    right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP].y]
    
    # Calculate shoulder midpoint
    shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, (left_shoulder[1] + right_shoulder[1]) / 2]
    
    # Calculate ear midpoint
    ear_mid = [(left_ear[0] + right_ear[0]) / 2, (left_ear[1] + right_ear[1]) / 2]
    
    # Calculate hip midpoint
    hip_mid = [(left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2]
    
    # 1. Head Forward Posture (Forward Head Posture)
    # Check if ear is significantly forward of shoulder
    ear_shoulder_diff = abs(ear_mid[0] - shoulder_mid[0])
    if ear_mid[0] < shoulder_mid[0] - 0.05:  # Threshold for forward head
        problems.append("Forward head posture detected")
    
    # 2. Neck angle calculation
    # Calculate angle between ear, shoulder, and hip
    neck_angle = calculate_angle(ear_mid, shoulder_mid, hip_mid)
    
    # 3. Shoulder alignment
    shoulder_height_diff = abs(left_shoulder[1] - right_shoulder[1])
    if shoulder_height_diff > 0.03:  # Threshold for uneven shoulders
        problems.append("Uneven shoulder height detected")
    
    # 4. Slouching detection
    # Check if shoulders are significantly forward of hips
    shoulder_hip_diff = abs(shoulder_mid[0] - hip_mid[0])
    if shoulder_mid[0] < hip_mid[0] - 0.08:  # Threshold for slouching
        problems.append("Slouching posture detected")
    
    # 5. Head tilt detection
    ear_height_diff = abs(left_ear[1] - right_ear[1])
    if ear_height_diff > 0.02:  # Threshold for head tilt
        problems.append("Head tilt detected")
    
    # Overall posture assessment
    bad_posture = len(problems) > 0
    
    return {
        'bad_posture': bad_posture,
        'neck_angle': neck_angle,
        'problems': problems,
        'shoulder_alignment': shoulder_height_diff,
        'forward_head_distance': ear_shoulder_diff
    }

def analyze_squat_posture(landmarks):
    """Analyze squat posture based on landmarks"""
    problems = []
    
    # Get key landmarks
    left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y]
    right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y]
    left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP].y]
    right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP].y]
    left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y]
    right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE].y]
    left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y]
    right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE].y]
    
    # Calculate knee angles
    left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
    right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
    
    # Calculate hip angles (hip-knee-ankle alignment)
    left_hip_angle = calculate_angle(left_shoulder, left_hip, left_knee)
    right_hip_angle = calculate_angle(right_shoulder, right_hip, right_knee)
    
    # 1. Knee angle assessment (should be around 90 degrees for proper squat)
    avg_knee_angle = (left_knee_angle + right_knee_angle) / 2
    if avg_knee_angle > 120:
        problems.append("Squat depth too shallow - go deeper")
    elif avg_knee_angle < 70:
        problems.append("Squat too deep - may strain knees")
    
    # 2. Knee alignment (knees should not cave inward)
    knee_distance = abs(left_knee[0] - right_knee[0])
    hip_distance = abs(left_hip[0] - right_hip[0])
    if knee_distance < hip_distance * 0.8:  # Knees caving in
        problems.append("Knee valgus detected - knees caving inward")
    
    # 3. Back angle assessment
    avg_hip_angle = (left_hip_angle + right_hip_angle) / 2
    if avg_hip_angle < 85:
        problems.append("Excessive forward lean - keep chest up")
    elif avg_hip_angle > 105:
        problems.append("Too upright - lean slightly forward")
    
    # 4. Ankle alignment
    ankle_knee_alignment = abs((left_ankle[0] - left_knee[0]) + (right_ankle[0] - right_knee[0])) / 2
    if ankle_knee_alignment > 0.05:
        problems.append("Poor ankle-knee alignment")
    
    # Overall posture assessment
    bad_posture = len(problems) > 0
    
    return {
        'bad_posture': bad_posture,
        'knee_angle': avg_knee_angle,
        'hip_angle': avg_hip_angle,
        'problems': problems,
        'knee_alignment_score': knee_distance / hip_distance if hip_distance > 0 else 1.0
    }

def analyze_posture(image_np, posture_type='sitting'):
    results_dict = {
        'analysis': {},
        'key_points': {},
        'landmarks_detected': False,
        'success': False
    }

    # Resize image if too large
    max_dim = 640
    if max(image_np.shape) > max_dim:
        scale = max_dim / max(image_np.shape)
        new_size = (int(image_np.shape[1] * scale), int(image_np.shape[0] * scale))
        image_np = cv2.resize(image_np, new_size, interpolation=cv2.INTER_AREA)

    try:
        with mp_pose.Pose(
            static_image_mode=True, 
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as pose:
            image_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark

                # Extract key points for display
                left_shoulder = [float(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x),
                                 float(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y)]
                right_shoulder = [float(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x),
                                  float(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y)]
                nose = [float(landmarks[mp_pose.PoseLandmark.NOSE].x),
                        float(landmarks[mp_pose.PoseLandmark.NOSE].y)]
                left_hip = [float(landmarks[mp_pose.PoseLandmark.LEFT_HIP].x),
                            float(landmarks[mp_pose.PoseLandmark.LEFT_HIP].y)]
                right_hip = [float(landmarks[mp_pose.PoseLandmark.RIGHT_HIP].x),
                             float(landmarks[mp_pose.PoseLandmark.RIGHT_HIP].y)]

                results_dict['key_points'] = {
                    'left_shoulder': left_shoulder,
                    'right_shoulder': right_shoulder,
                    'nose': nose,
                    'left_hip': left_hip,
                    'right_hip': right_hip
                }

                # Perform posture analysis based on type
                if posture_type == 'sitting':
                    analysis = analyze_sitting_posture(landmarks)
                elif posture_type == 'squat':
                    analysis = analyze_squat_posture(landmarks)
                else:
                    analysis = analyze_sitting_posture(landmarks)  # Default to sitting

                results_dict['analysis'] = analysis
                results_dict['landmarks_detected'] = True
                results_dict['success'] = True
                
            else:
                results_dict['analysis'] = {
                    'bad_posture': False,
                    'problems': ['No pose landmarks detected - please ensure full body is visible']
                }
                results_dict['success'] = True

    except Exception as e:
        results_dict['error'] = str(e)
        results_dict['success'] = False

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

@app.route('/analyze_video', methods=['POST'])
def analyze_video():
    posture_type = request.form.get('posture_type', 'sitting')
    
    if 'video' not in request.files:
        return jsonify({'error': 'No video uploaded'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            file.save(tmp.name)
            
            # Process video
            cap = cv2.VideoCapture(tmp.name)
            
            if not cap.isOpened():
                return jsonify({'error': 'Failed to load video'}), 400
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            analyzed_frames = 0
            bad_posture_count = 0
            all_problems = []
            
            # Analyze every 10th frame to reduce processing time
            frame_skip = max(1, total_frames // 100)  # Analyze max 100 frames
            
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
            
            # Calculate statistics
            bad_posture_percentage = (bad_posture_count / analyzed_frames * 100) if analyzed_frames > 0 else 0
            
            # Count problem frequency
            problem_counts = {}
            for problem in all_problems:
                problem_counts[problem] = problem_counts.get(problem, 0) + 1
            
            # Sort problems by frequency
            main_issues = sorted(problem_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Overall rating
            overall_rating = 'good' if bad_posture_percentage < 30 else 'bad'
            
            results = {
                'total_frames': total_frames,
                'analyzed_frames': analyzed_frames,
                'bad_posture_percentage': bad_posture_percentage,
                'summary': {
                    'overall_rating': overall_rating,
                    'main_issues': main_issues
                }
            }
            
            return jsonify(results)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if tmp and os.path.exists(tmp.name):
            os.remove(tmp.name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
