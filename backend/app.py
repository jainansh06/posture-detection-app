from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import tempfile
import os
import gc
import math

# Create Flask app instance first
app = Flask(__name__)

# Then configure CORS
CORS(app, origins=[
    "https://posture-detection-app-dun.vercel.app",
    "http://localhost:3000",  # for local development
    "http://localhost:3001"   # backup local port
])

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
