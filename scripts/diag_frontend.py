import os
import sys
sys.path.insert(0, "/app")
fb = os.path.join(os.path.dirname("/app/app/main.py"), "..", "..", "frontend", "build")
fb = os.path.normpath(fb)
print("FRONTEND_BUILD:", fb)
print("exists:", os.path.isdir(fb))
if os.path.isdir(fb):
    print("contents:", os.listdir(fb))
    app_dir = os.path.join(fb, "_app")
    print("_app exists:", os.path.isdir(app_dir))
    if os.path.isdir(app_dir):
        print("_app contents:", os.listdir(app_dir))
