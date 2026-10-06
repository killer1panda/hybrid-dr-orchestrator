"""Mock On-Premises Service for Local Trial on Windows.

Simulates the 3-tier workload (Nginx reverse proxy + FastAPI backend + DB)
on port 8080 for running end-to-end quorum detection and drills without Docker.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Mock On-Premises Application (Local Trial)")

_is_healthy = True
_read_only = False
_items: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "sample-order-101",
        "description": "pre-failover seed transaction",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
]


class ItemCreate(BaseModel):
    name: str
    description: str | None = None


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    global _is_healthy, _read_only
    if not _is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "node": "onprem-app-1", "db": {"connected": False}},
        )
    if _read_only:
        return {
            "status": "degraded_fenced",
            "node": "onprem-app-1",
            "db": {"connected": True, "read_only": True, "status": "degraded"},
            "message": "Site is in read-only fencing state",
        }
    return {
        "status": "ok",
        "node": "onprem-app-1",
        "db": {"connected": True, "read_only": False, "status": "healthy"},
    }


@app.get("/items")
def get_items() -> list[dict[str, Any]]:
    return _items


@app.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate) -> dict[str, Any]:
    global _read_only
    if _read_only:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is in read-only mode (fenced)",
        )
    new_item = {
        "id": len(_items) + 1,
        "name": item.name,
        "description": item.description,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _items.append(new_item)
    return new_item


@app.post("/chaos/blackout")
def trigger_blackout() -> dict[str, str]:
    global _is_healthy
    _is_healthy = False
    return {"status": "blackout_injected", "message": "On-premise healthz returning 503"}


@app.post("/chaos/recover")
def trigger_recover() -> dict[str, str]:
    global _is_healthy, _read_only
    _is_healthy = True
    _read_only = False
    return {"status": "recovered", "message": "On-premise service restored to healthy"}


@app.post("/fencing/lock")
def fence_site() -> dict[str, str]:
    global _read_only
    _read_only = True
    return {"status": "fenced", "message": "On-premise database set to read-only"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Mock On-Premises Service")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    args = parser.parse_args()

    print(f"Starting Mock On-Premises Service on http://{args.host}:{args.port}...")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
