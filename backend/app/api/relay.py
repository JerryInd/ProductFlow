import json
import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

RELAY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "whatsapp-relay")
STATUS_FILE = os.path.join(RELAY_DIR, "status.json")
PROMPT_FILE = os.path.join(RELAY_DIR, "prompt.txt")
ENV_FILE = os.path.join(RELAY_DIR, ".env")


class RelayConfig(BaseModel):
    prompt: str
    markup: int


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


@router.get("/config")
def get_config():
    prompt = ""
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r") as f:
            prompt = f.read()

    markup = 1000
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.startswith("MARKUP="):
                    try:
                        markup = int(line.strip().split("=", 1)[1])
                    except ValueError:
                        pass

    return {"prompt": prompt, "markup": markup}


@router.put("/config")
def update_config(config: RelayConfig):
    with open(PROMPT_FILE, "w") as f:
        f.write(config.prompt)

    if os.path.exists(ENV_FILE):
        lines = []
        found = False
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.startswith("MARKUP="):
                    lines.append(f"MARKUP={config.markup}\n")
                    found = True
                else:
                    lines.append(line)
        if not found:
            lines.append(f"MARKUP={config.markup}\n")
        with open(ENV_FILE, "w") as f:
            f.writelines(lines)

    return {"message": "Config updated. Relay monitor will use new prompt on next message."}
