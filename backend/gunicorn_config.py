import os

#bind = "0.0.0.0:5000" aws
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1
threads = 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# Additional settings for production (not aws)
preload_app = True
worker_tmp_dir = "/dev/shm"
