from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import tempfile
import os
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)
CORS(app)

# Initialize MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

@app.route('/')
def home():
    return jsonify({"message": "Posture Detection API is running!", "status": "healthy"})

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

def analyze_posture(image_array):
    """Analyze posture from image array"""
    try:
        with mp_pose.Pose(
            static_image_mode=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as pose:
            
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb_image)
            
            if not results.pose_landmarks:
                return {
                    "success": False,
                    "error": "No person detected in the image"
                }
            
            # Get key landmarks
            landmarks = results.pose_landmarks.landmark
            
            # Extract key points
            nose = [landmarks[mp_pose.PoseLandmark.NOSE].x, landmarks[mp_pose.PoseLandmark.NOSE].y]
            left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y]
            right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y]
            left_ear = [landmarks[mp_pose.PoseLandmark.LEFT_EAR].x, landmarks[mp_pose.PoseLandmark.LEFT_EAR].y]
            right_ear = [landmarks[mp_pose.PoseLandmark.RIGHT_EAR].x, landmarks[mp_pose.PoseLandmark.RIGHT_EAR].y]
            
            # Calculate midpoints
            shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, (left_shoulder[1] + right_shoulder[1]) / 2]
            ear_mid = [(left_ear[0] + right_ear[0]) / 2, (left_ear[1] + right_ear[1]) / 2]
            
            # Analyze posture
            issues = []
            
            # Check for forward head posture
            if ear_mid[0] < shoulder_mid[0] - 0.05:
                issues.append("Forward head posture detected")
            
            # Check shoulder alignment
            shoulder_height_diff = abs(left_shoulder[1] - right_shoulder[1])
            if shoulder_height_diff > 0.03:
                issues.append("Uneven shoulder height")
            
            # Check head tilt
            ear_height_diff = abs(left_ear[1] - right_ear[1])
            if ear_height_diff > 0.02:
                issues.append("Head tilt detected")
            
            # Determine overall posture
            posture_score = max(0, 100 - (len(issues) * 25))
            posture_rating = "Excellent" if posture_score >= 90 else "Good" if posture_score >= 70 else "Fair" if posture_score >= 50 else "Poor"
            
            return {
                "success": True,
                "posture_score": posture_score,
                "posture_rating": posture_rating,
                "issues": issues,
                "landmarks_detected": True
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}"
        }

@app.route('/analyze', methods=['POST'])
def analyze_image():
    """Analyze posture from uploaded image"""
    try:
        # Check if image is in request
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "No image provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"success": False, "error": "No image selected"}), 400
        
        # Read image
        image_bytes = file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({"success": False, "error": "Invalid image format"}), 400
        
        # Analyze posture
        result = analyze_posture(image)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/analyze_base64', methods=['POST'])
def analyze_base64_image():
    """Analyze posture from base64 encoded image"""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"success": False, "error": "No image data provided"}), 400
        
        # Decode base64 image
        image_data = data['image']
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        image_array = np.array(image)
        
        # Convert RGB to BGR for OpenCV
        if len(image_array.shape) == 3:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        # Analyze posture
        result = analyze_posture(image_array)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
