import os
import logging
from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db, verify_db_connection
from app.models import Item, RPOProbe

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("app")

NODE_NAME = os.getenv("NODE_NAME", "onprem-app-1")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting app on node %s; verifying schemas...", NODE_NAME)
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down application...")

app = FastAPI(title="Hybrid DR Sample 3-Tier Workload", version="1.0.0", lifespan=lifespan)

class ItemCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: str | None = None

class ItemResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: str
    class Config:
        from_attributes = True

@app.get("/healthz", status_code=status.HTTP_200_OK)
def health_check():
    db_status = verify_db_connection()
    if not db_status["connected"]:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"status": "unhealthy", "node": NODE_NAME, "db": db_status})
    if db_status["read_only"]:
        return {"status": "degraded_fenced", "node": NODE_NAME, "db": db_status, "message": "Site is in read-only fencing state"}
    return {"status": "ok", "node": NODE_NAME, "db": db_status}

@app.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item_in: ItemCreate, db: Session = Depends(get_db)):
    item = Item(name=item_in.name, description=item_in.description)
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
        return ItemResponse(id=item.id, name=item.name, description=item.description, created_at=item.created_at.isoformat())
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database write error: {exc}")

@app.get("/items", response_model=List[ItemResponse])
def list_items(db: Session = Depends(get_db)):
    items = db.query(Item).order_by(Item.id.desc()).limit(100).all()
    return [ItemResponse(id=it.id, name=it.name, description=it.description, created_at=it.created_at.isoformat()) for it in items]

@app.get("/probe/latest")
def get_latest_probe(db: Session = Depends(get_db)):
    probe = db.query(RPOProbe).order_by(RPOProbe.probe_id.desc()).first()
    if not probe:
        return {"status": "empty", "probe": None}
    return {"probe_id": probe.probe_id, "written_at_utc": probe.written_at_utc.isoformat(), "cluster_node": probe.cluster_node}
