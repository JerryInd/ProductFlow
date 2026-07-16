from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.connection import get_connection
from app.utils.helpers import serialize_row

router = APIRouter()

class PipelineCreate(BaseModel):
    name: str
    prompt_template: str = ""
    pricing_mode: str = "percentage"
    pricing_value: float = 0
    pricing_tiers: str | None = None
    collector_window_seconds: int = 90
    auto_publish: bool = True
    draft_mode: bool = False
    enabled: bool = True
    source_group_ids: list[str] = []
    destination_group_ids: list[str] = []

class PipelineUpdate(BaseModel):
    name: str | None = None
    prompt_template: str | None = None
    pricing_mode: str | None = None
    pricing_value: float | None = None
    pricing_tiers: str | None = None
    collector_window_seconds: int | None = None
    auto_publish: bool | None = None
    draft_mode: bool | None = None
    enabled: bool | None = None

@router.get("/")
def list_pipelines():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM pipelines ORDER BY name").fetchall()
    result = []
    for r in rows:
        p = serialize_row(r)
        p["sources"] = [
            dict(s) for s in conn.execute(
                "SELECT group_id FROM pipeline_sources WHERE pipeline_id = ?", (r["id"],)
            ).fetchall()
        ]
        p["destinations"] = [
            dict(s) for s in conn.execute(
                "SELECT group_id FROM pipeline_destinations WHERE pipeline_id = ?", (r["id"],)
            ).fetchall()
        ]
        result.append(p)
    conn.close()
    return result

@router.post("/")
def create_pipeline(body: PipelineCreate):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO pipelines (name, prompt_template, pricing_mode, pricing_value,
           pricing_tiers, collector_window_seconds, auto_publish, draft_mode, enabled)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (body.name, body.prompt_template, body.pricing_mode, body.pricing_value,
         body.pricing_tiers, body.collector_window_seconds,
         int(body.auto_publish), int(body.draft_mode), int(body.enabled)),
    )
    pid = cur.lastrowid
    for gid in body.source_group_ids:
        conn.execute("INSERT OR IGNORE INTO pipeline_sources (pipeline_id, group_id) VALUES (?, ?)", (pid, gid))
    for gid in body.destination_group_ids:
        conn.execute("INSERT OR IGNORE INTO pipeline_destinations (pipeline_id, group_id) VALUES (?, ?)", (pid, gid))
    conn.commit()
    conn.close()
    return {"id": pid, "message": "Pipeline created"}

@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Pipeline not found")
    p = serialize_row(row)
    p["sources"] = [
        dict(s) for s in conn.execute(
            "SELECT group_id FROM pipeline_sources WHERE pipeline_id = ?", (pipeline_id,)
        ).fetchall()
    ]
    p["destinations"] = [
        dict(s) for s in conn.execute(
            "SELECT group_id FROM pipeline_destinations WHERE pipeline_id = ?", (pipeline_id,)
        ).fetchall()
    ]
    conn.close()
    return p

@router.put("/{pipeline_id}")
def update_pipeline(pipeline_id: int, body: PipelineUpdate):
    conn = get_connection()
    existing = conn.execute("SELECT id FROM pipelines WHERE id = ?", (pipeline_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Pipeline not found")
    updates = body.model_dump(exclude_none=True)
    if updates:
        sets = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [pipeline_id]
        conn.execute(f"UPDATE pipelines SET {sets}, updated_at = datetime('now') WHERE id = ?", values)
        conn.commit()
    conn.close()
    return {"message": "Pipeline updated"}

@router.delete("/{pipeline_id}")
def delete_pipeline(pipeline_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM queue WHERE pipeline_id = ?", (pipeline_id,))
    conn.execute("DELETE FROM active_collections WHERE pipeline_id = ?", (pipeline_id,))
    conn.execute("UPDATE products SET pipeline_id = NULL WHERE pipeline_id = ?", (pipeline_id,))
    conn.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
    conn.commit()
    conn.close()
    return {"message": "Pipeline deleted"}
