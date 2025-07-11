import os

# Bind to consistent Render port (default 10000 as aligned with app.py)
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Safe settings for low-RAM Render plans
workers = 1
threads = 1
worker_class = "sync"  # keep "sync" for Mediapipe stability

# Extend timeout to handle slow uploads & Mediapipe processing
timeout = 180
keepalive = 5

# Manage memory leaks gracefully
max_requests = 500
max_requests_jitter = 50

# Avoid preload to reduce initial memory spike on Render
preload_app = False

# Faster temporary file handling
worker_tmp_dir = "/dev/shm"
