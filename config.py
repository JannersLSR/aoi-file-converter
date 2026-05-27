import json
from pathlib import Path

SETTINGS_FILE = Path("settings.json")
HISTORY_FILE = Path("history.json")

DEFAULT_SETTINGS = {
    "default_output_dir": "",  # Empty means same as source file
    "overwrite_existing": True,
    "video_crf": "23",
    "video_preset": "fast",
    "gif_fps": "15",
    "gif_width": "480"
}

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception:
        pass

def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[-20:], f, indent=4) # Keep last 20 entries
    except Exception:
        pass
