from fastapi import APIRouter, HTTPException, Query
from app.database.connection import get_connection
from app.utils.helpers import serialize_row

router = APIRouter()

@router.get("/")
def list_products(
    status: str = Query("", max_length=20),
    pipeline_id: int | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    conn = get_connection()
    where = []
    params = []
    if status:
        where.append("p.status = ?")
        params.append(status)
    if pipeline_id:
        where.append("p.pipeline_id = ?")
        params.append(pipeline_id)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = conn.execute(
        f"SELECT p.*, q.status as queue_status FROM products p LEFT JOIN queue q ON q.product_id = p.id {clause} ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    return {"products": [serialize_row(r) for r in rows], "total": total}

@router.get("/{product_id}")
def get_product(product_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_row(row)

@router.post("/{product_id}/approve")
def approve_product(product_id: int):
    conn = get_connection()
    conn.execute("UPDATE queue SET status = 'queued' WHERE product_id = ? AND status = 'draft'", (product_id,))
    conn.execute("UPDATE products SET status = 'approved', updated_at = datetime('now') WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"message": "Product approved for publishing"}

@router.post("/{product_id}/reject")
def reject_product(product_id: int):
    conn = get_connection()
    conn.execute("UPDATE queue SET status = 'rejected' WHERE product_id = ?", (product_id,))
    conn.execute("UPDATE products SET status = 'rejected', updated_at = datetime('now') WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"message": "Product rejected"}
