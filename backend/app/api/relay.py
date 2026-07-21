import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
BRIDGE_STATUS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "whatsapp-bridge", "relay-status.json")
PIPELINES_FILE = os.path.join(DATA_DIR, "relay_pipelines.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)


class RelayPipeline(BaseModel):
    id: int = 0
    name: str
    enabled: bool = True
    source_groups: List[str] = []
    destination_group: str = ""
    markup: int = 1000
    prompt: str = ""


class RelayProcessRequest(BaseModel):
    text: str


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


DEFAULT_PROMPT = """You are a WhatsApp product post editor.

MARKUP = {markup}

TASK

Edit the supplied WhatsApp product post by following these rules exactly.

RULES

1. Find the MAIN SELLING PRICE.
   The main selling price is usually:
   - The only product price in the post.
   - The price after words like Price, Rs, Rate, Available, Available@, Only.
   - The primary selling price of the product.

2. Ignore prices related to:
   - Shipping, OG Box, Indian Box, Accessories, Dust Cover, Invoice, Extra Charges, Any optional add-ons.

3. Extract only the numeric value of the main selling price.

4. Remove commas from the number if present.

5. Add MARKUP to the extracted price.

6. Replace ONLY the main selling price with the calculated price.

7. Preserve the original price format.

8. Remove every line that contains any of the following:
   - http, https, www, Place Orders, Product Direct Link, Order Here, Buy Now, Checkout, Cart, Store Link

9. Remove any empty blank lines created after deleting text.

10. Append this footer exactly:

━━━━━━━━━━━━━━
🔥 Perfect Deals 🔥
Premium Quality Products
📦 Pan India Shipping

WhatsApp:
+918169858589
https://chat.whatsapp.com/Khx2ym45DSy1AXfp3XtY86

Posted by |NotJerry|
━━━━━━━━━━━━━━

11. Do NOT change: Product title, Brand name, Description, Features, Specifications, Size, Quality, Emojis, Hashtags, Formatting, Existing line breaks.

12. Return ONLY the final edited WhatsApp post."""


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
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 512,
                    "temperature": 0.3,
                },
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return text


@router.post("/process")
async def process_message(req: RelayProcessRequest):
    pipelines = load_pipelines()
    matched = []
    for p in pipelines:
        if not p.get("enabled"):
            continue
        prompt = p.get("prompt", "").format(markup=p.get("markup", 1000))
        if not prompt:
            prompt = DEFAULT_PROMPT.format(markup=p.get("markup", 1000))
        rewritten = await call_groq(prompt, req.text)
        matched.append({
            "id": p["id"],
            "name": p["name"],
            "rewritten": rewritten,
            "destination_group": p.get("destination_group", ""),
        })
    return {"matched": len(matched) > 0, "pipelines": matched}


@router.get("/pipelines")
def list_pipelines():
    return load_pipelines()


@router.post("/pipelines")
def create_pipeline(data: RelayPipeline):
    pipelines = load_pipelines()
    new_id = max([p["id"] for p in pipelines], default=0) + 1
    pipeline = {"id": new_id, **data.model_dump()}
    pipelines.append(pipeline)
    save_pipelines(pipelines)
    return pipeline


@router.put("/pipelines/{pipeline_id}")
def update_pipeline(pipeline_id: int, data: RelayPipeline):
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


@router.get("/status")
def relay_status():
    pipelines = load_pipelines()
    connected = False
    mode = "offline"
    try:
        if os.path.exists(BRIDGE_STATUS_FILE):
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
                "source_groups": p.get("source_groups", []),
                "destination_group": p.get("destination_group", ""),
                "markup": p.get("markup", 1000),
            }
            for p in pipelines
        ],
        "processed_count": 0,
    }
