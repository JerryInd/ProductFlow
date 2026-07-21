import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

RELAY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "whatsapp-relay")
STATUS_FILE = os.path.join(RELAY_DIR, "status.json")
PIPELINES_FILE = os.path.join(RELAY_DIR, "pipelines.json")
ENV_FILE = os.path.join(RELAY_DIR, ".env")


class RelayPipeline(BaseModel):
    id: int
    name: str
    enabled: bool = True
    source_groups: List[str] = []
    destination_group: str = ""
    markup: int = 1000
    prompt_file: str = "prompt.txt"


class RelayPipelineCreate(BaseModel):
    name: str
    enabled: bool = True
    source_groups: List[str] = []
    destination_group: str = ""
    markup: int = 1000
    prompt_file: str = "prompt.txt"


def load_pipelines() -> list:
    if not os.path.exists(PIPELINES_FILE):
        return []
    try:
        with open(PIPELINES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_pipelines(pipelines: list):
    with open(PIPELINES_FILE, "w") as f:
        json.dump(pipelines, f, indent=2)


@router.get("/status")
def relay_status():
    if not os.path.exists(STATUS_FILE):
        return {
            "connected": False,
            "catching_up": False,
            "mode": "offline",
            "pipelines": [],
            "processed_count": 0,
            "last_update": None,
            "last_scan": None,
            "error": "Relay monitor not running",
        }
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.get("/pipelines")
def list_pipelines():
    return load_pipelines()


@router.post("/pipelines")
def create_pipeline(data: RelayPipelineCreate):
    pipelines = load_pipelines()
    new_id = max([p["id"] for p in pipelines], default=0) + 1
    pipeline = {"id": new_id, **data.model_dump()}
    pipelines.append(pipeline)
    save_pipelines(pipelines)
    return pipeline


@router.put("/pipelines/{pipeline_id}")
def update_pipeline(pipeline_id: int, data: RelayPipelineCreate):
    pipelines = load_pipelines()
    for i, p in enumerate(pipelines):
        if p["id"] == pipeline_id:
            pipelines[i] = {"id": pipeline_id, **data.model_dump()}
            save_pipelines(pipelines)
            return pipelines[i]
    raise HTTPException(status_code=404, detail="Pipeline not found")


@router.delete("/pipelines/{pipeline_id}")
def delete_pipeline(pipeline_id: int):
    pipelines = load_pipelines()
    pipelines = [p for p in pipelines if p["id"] != pipeline_id]
    save_pipelines(pipelines)
    return {"message": "Deleted"}


@router.get("/config")
def get_config():
    markup = 1000
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.startswith("MARKUP="):
                    try:
                        markup = int(line.strip().split("=", 1)[1])
                    except ValueError:
                        pass
    return {"markup": markup}
