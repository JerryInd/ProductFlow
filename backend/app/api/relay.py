import os
import json
import time
import asyncio
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List
from ..database.connection import get_connection

router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
BRIDGE_STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "relay-status.json")
RETRY_QUEUE_FILE = os.path.join(DATA_DIR, "relay-retry-queue.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)


class RelayProcessRequest(BaseModel):
    text: str
    group_name: str = ""
    group_id: str = ""


def load_pipelines() -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT p.id, p.name, p.enabled, p.prompt_template, p.pricing_mode,
                      p.pricing_value, p.collector_window_seconds, p.auto_publish, p.draft_mode,
                      GROUP_CONCAT(DISTINCT ps.group_id) as source_group_ids,
                      GROUP_CONCAT(DISTINCT pd.group_id) as dest_group_ids
               FROM pipelines p
               LEFT JOIN pipeline_sources ps ON p.id = ps.pipeline_id
               LEFT JOIN pipeline_destinations pd ON p.id = pd.pipeline_id
               GROUP BY p.id"""
        ).fetchall()
        pipelines = []
        for r in rows:
            source_ids = [x for x in (r["source_group_ids"] or "").split(",") if x]
            dest_ids = [x for x in (r["dest_group_ids"] or "").split(",") if x]
            pipelines.append({
                "id": r["id"],
                "name": r["name"],
                "enabled": r["enabled"],
                "prompt_template": r["prompt_template"] or "",
                "pricing_mode": r["pricing_mode"] or "fixed",
                "pricing_value": r["pricing_value"] or 0.0,
                "auto_publish": r["auto_publish"],
                "draft_mode": r["draft_mode"],
                "source_group_ids": source_ids,
                "dest_group_ids": dest_ids,
            })
        return pipelines
    finally:
        conn.close()


NO_PRICE_PATTERNS = [
    "there is no price",
    "no price found",
    "no price in the post",
    "cannot find a price",
    "no selling price",
    "no main price",
    "price not found",
    "unable to find",
]

PREAMBLE_PATTERNS = [
    "since there is no",
    "since no text",
    "since no product",
    "i will append",
    "i will add",
    "i will edit",
    "i will provide",
    "i will output",
    "i will generate",
    "i will create",
    "i will rewrite",
    "i will just",
    "here is the",
    "here is your",
    "below is the",
    "below is your",
    "the edited post",
    "the rewritten post",
    "the modified post",
    "the updated post",
    "as requested",
    "as per your",
    "as per the",
    "there is no text",
    "there is no product",
    "no text or product",
    "no content to edit",
    "nothing to edit",
    "i'll append",
    "i'll add",
    "i'll edit",
    "i'll provide",
]


def strip_ai_preamble(text: str) -> str:
    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines):
        lower = line.lower().strip()
        if any(p in lower for p in PREAMBLE_PATTERNS):
            start = i + 1
        elif start > 0:
            break
    if start > 0:
        result = "\n".join(lines[start:]).strip()
        if result:
            return result
    return text


def contains_no_price_signal(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in NO_PRICE_PATTERNS)


async def call_groq(prompt: str, text: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    if not api_key:
        return text
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "ProductFlow/1.0",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt + "\n\nCRITICAL: Output ONLY the edited product post. No preamble, no explanation, no 'I will...' text, no 'Since there is no...' text. Just the final post."},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 512,
                    "temperature": 0.3,
                },
            )
            data = resp.json()
            result = data["choices"][0]["message"]["content"].strip()
            result = strip_ai_preamble(result)
            if contains_no_price_signal(result):
                return ""
            return result
    except Exception as e:
        print(f"Groq error: {e}")
        return text


def build_prompt(p: dict) -> str:
    prompt = p.get("prompt_template", "")
    if not prompt:
        return ""
    return prompt


def matches_pipeline(p: dict, group_name: str, group_id: str) -> bool:
    source_ids = p.get("source_group_ids", [])
    if not source_ids:
        return False
    if group_id and group_id in source_ids:
        return True
    if group_name:
        conn = get_connection()
        try:
            row = conn.execute("SELECT group_id FROM groups WHERE TRIM(group_name) = TRIM(?)", (group_name,)).fetchone()
            if row and row["group_id"] in source_ids:
                if group_id and group_id != row["group_id"]:
                    conn.execute("UPDATE groups SET group_id=? WHERE group_id=?", (group_id, row["group_id"]))
                    conn.execute("UPDATE pipeline_sources SET group_id=? WHERE group_id=?", (group_id, row["group_id"]))
                    conn.commit()
                return True
        except Exception:
            pass
        finally:
            conn.close()
    return False


@router.post("/process")
async def process_message(req: RelayProcessRequest):
    pipelines = load_pipelines()
    matched = []
    for p in pipelines:
        if not p.get("enabled"):
            continue
        if not matches_pipeline(p, req.group_name, req.group_id):
            continue
        prompt = build_prompt(p)
        if not prompt:
            continue
        if req.text == "(media)":
            rewritten = ""
        else:
            rewritten = await call_groq(prompt, req.text)
        matched.append({
            "id": p["id"],
            "name": p["name"],
            "rewritten": rewritten,
            "dest_group_ids": p.get("dest_group_ids", []),
        })
    return {"matched": len(matched) > 0, "pipelines": matched}


@router.get("/status")
def relay_status():
    pipelines = load_pipelines()
    connected = False
    mode = "offline"
    try:
        if os.path.exists(BRIDGE_STATUS_FILE):
            import json
            with open(BRIDGE_STATUS_FILE, "r") as f:
                bs = json.load(f)
            connected = bs.get("connected", False)
            mode = bs.get("mode", "offline")
    except Exception:
        pass
    return {
        "connected": connected,
        "mode": mode,
        "pipelines": [
            {
                "id": p["id"],
                "name": p["name"],
                "enabled": p.get("enabled", True),
                "source_group_ids": p.get("source_group_ids", []),
                "dest_group_ids": p.get("dest_group_ids", []),
            }
            for p in pipelines
        ],
        "processed_count": 0,
    }


@router.post("/test")
async def test_relay(req: RelayProcessRequest):
    pipelines = load_pipelines()
    matched = []
    for p in pipelines:
        if not p.get("enabled"):
            continue
        if not matches_pipeline(p, req.group_name, req.group_id):
            continue
        prompt = build_prompt(p)
        if not prompt:
            continue
        if req.text == "(media)":
            rewritten = ""
        else:
            rewritten = await call_groq(prompt, req.text)
        matched.append({
            "id": p["id"],
            "name": p["name"],
            "rewritten": rewritten,
            "dest_group_ids": p.get("dest_group_ids", []),
        })
    return {"matched": len(matched) > 0, "pipelines": matched}


# --- Retry Queue ---

class RetryQueueItem(BaseModel):
    text: str
    group_name: str = ""
    group_id: str = ""
    has_media: bool = False
    caption: str = ""
    dest_group_ids: list[str] = []
    pipeline_name: str = ""
    error: str = ""


def load_retry_queue() -> list:
    if os.path.exists(RETRY_QUEUE_FILE):
        try:
            with open(RETRY_QUEUE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_retry_queue(queue: list):
    with open(RETRY_QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def add_to_retry_queue(item: dict):
    queue = load_retry_queue()
    item["added_at"] = time.time()
    item["retries"] = 0
    queue.append(item)
    save_retry_queue(queue)
    print(f"[RetryQueue] Added task (total: {len(queue)})")


def remove_from_retry_queue(index: int):
    queue = load_retry_queue()
    if 0 <= index < len(queue):
        queue.pop(index)
        save_retry_queue(queue)


@router.post("/queue")
async def add_retry_item(item: RetryQueueItem):
    add_to_retry_queue(item.model_dump())
    return {"ok": True, "message": "Added to retry queue"}


@router.get("/queue")
async def get_retry_queue():
    queue = load_retry_queue()
    return {"count": len(queue), "items": queue}


@router.delete("/queue")
async def clear_retry_queue():
    save_retry_queue([])
    return {"ok": True, "message": "Queue cleared"}


async def process_retry_queue():
    queue = load_retry_queue()
    if not queue:
        return

    print(f"[RetryQueue] Processing {len(queue)} queued tasks...")
    processed = []

    for i, item in enumerate(queue):
        try:
            text = item.get("text", "")
            group_name = item.get("group_name", "")
            group_id = item.get("group_id", "")

            pipelines = load_pipelines()
            matched = False
            for p in pipelines:
                if not p.get("enabled"):
                    continue
                if not matches_pipeline(p, group_name, group_id):
                    continue
                prompt = build_prompt(p)
                if not prompt:
                    continue
                if text == "(media)":
                    rewritten = ""
                else:
                    rewritten = await call_groq(prompt, text)
                matched = True
                print(f"[RetryQueue] Rewrote for {p['name']}: {rewritten[:50]}...")
                break

            if matched:
                processed.append(i)
                print(f"[RetryQueue] Task {i} processed successfully")
            else:
                item["retries"] = item.get("retries", 0) + 1
                if item["retries"] >= 5:
                    processed.append(i)
                    print(f"[RetryQueue] Task {i} max retries reached, removing")
        except Exception as e:
            print(f"[RetryQueue] Task {i} failed: {e}")
            item["retries"] = item.get("retries", 0) + 1
            if item["retries"] >= 5:
                processed.append(i)

    # Remove processed items (in reverse order to preserve indices)
    for i in sorted(processed, reverse=True):
        queue.pop(i)
    save_retry_queue(queue)
    print(f"[RetryQueue] Done. {len(processed)} processed, {len(queue)} remaining")


@router.post("/queue/process")
async def trigger_queue_processing():
    await process_retry_queue()
    return {"ok": True, "message": "Queue processed"}


async def start_queue_processor():
    await asyncio.sleep(10)
    while True:
        try:
            queue = load_retry_queue()
            if queue:
                await process_retry_queue()
        except Exception as e:
            print(f"[RetryQueue] Processor error: {e}")
        await asyncio.sleep(60)
