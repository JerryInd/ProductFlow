import json
import urllib.request
from fastapi import APIRouter, HTTPException, Query
from app.database.connection import get_connection
from app.utils.helpers import serialize_row

router = APIRouter()
BRIDGE_URL = "http://localhost:8001"

@router.get("/")
def list_groups(search: str = Query("", max_length=100)):
    conn = get_connection()
    if search:
        rows = conn.execute(
            "SELECT * FROM groups WHERE group_name LIKE ? ORDER BY group_name",
            (f"%{search}%",),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM groups WHERE id IN (SELECT MAX(id) FROM groups GROUP BY group_name) ORDER BY group_name"
        ).fetchall()
    conn.close()
    return [serialize_row(r) for r in rows]

@router.get("/{group_id}")
def get_group(group_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM groups WHERE group_id = ?", (group_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    return serialize_row(row)

@router.post("/sync")
def sync_groups():
    try:
        req = urllib.request.Request(
            f"{BRIDGE_URL}/groups",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
    except Exception as e:
        return {"message": f"Bridge unavailable: {e}", "synced": 0}

    if not result.get("ok"):
        return {"message": "Bridge returned error", "synced": 0}

    groups = result.get("groups", [])
    conn = get_connection()
    synced = 0
    for g in groups:
        gid = g.get("group_id", "")
        gname = g.get("group_name", gid)
        if not gid:
            continue
        existing = conn.execute("SELECT id FROM groups WHERE group_id = ?", (gid,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE groups SET group_name = ?, member_count = ?, last_activity = datetime('now') WHERE group_id = ?",
                (gname, g.get("member_count", 0), gid),
            )
        else:
            # Check if a group with the same name already exists (different group_id)
            same_name = conn.execute("SELECT id FROM groups WHERE group_name = ?", (gname,)).fetchone()
            if same_name:
                continue
            conn.execute(
                "INSERT INTO groups (group_id, group_name, member_count, last_activity) VALUES (?, ?, ?, datetime('now'))",
                (gid, gname, g.get("member_count", 0)),
            )
        synced += 1
    conn.commit()
    conn.close()
    return {"message": f"Synced {synced} groups", "synced": synced}
