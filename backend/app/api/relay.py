import json
import os
from fastapi import APIRouter

router = APIRouter()

STATUS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "whatsapp-relay", "status.json")
PROCESSED_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "whatsapp-relay", "processed.json")


@router.get("/status")
def relay_status():
    if not os.path.exists(STATUS_FILE):
        return {
            "connected": False,
            "catching_up": False,
            "mode": "offline",
            "source_groups": [],
            "destination_group": "",
            "processed_count": 0,
            "last_update": None,
            "last_scan": None,
            "error": "Relay monitor not running or no status file found",
        }
    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"connected": False, "error": str(e)}
