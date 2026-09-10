import sys
from pathlib import Path

# Ensure backend root is always on sys.path for test discovery and imports
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
