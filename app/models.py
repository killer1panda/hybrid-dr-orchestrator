from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, text
from app.database import Base

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(128), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

class RPOProbe(Base):
    __tablename__ = "rpo_probe"
    probe_id = Column(BigInteger, primary_key=True, autoincrement=True)
    written_at_utc = Column(DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()"), index=True)
    cluster_node = Column(String(64), nullable=False)
