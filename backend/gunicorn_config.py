import os

# Bind to the Render-provided port or default to 5000 locally
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Worker and threading configuration
workers = 1
threads = 2
worker_class = "gthread"

# Connection & lifecycle settings
worker_connections = 1000
timeout = 120
keepalive = 5

# Automatic recycling to avoid memory leaks
max_requests = 1000
max_requests_jitter = 100

# Production optimizations
preload_app = True
worker_tmp_dir = "/dev/shm"
