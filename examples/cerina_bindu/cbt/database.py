"""
Database setup and utilities for persistence
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

Base = declarative_base()

class ProtocolSession(Base):
    """Database model for protocol generation sessions"""
    __tablename__ = "protocol_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    user_intent = Column(Text)
    status = Column(String)
    current_draft = Column(Text, nullable=True)
    final_protocol = Column(Text, nullable=True)
    safety_score = Column(Float, nullable=True)
    empathy_score = Column(Float, nullable=True)
    clinical_score = Column(Float, nullable=True)
    iteration_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    meta_data = Column(JSON, default=dict)  # Renamed from 'metadata' to avoid SQLAlchemy reserved word conflict

class AgentActivity(Base):
    """Log of agent activities for history tracking"""
    __tablename__ = "agent_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    agent_name = Column(String)
    action = Column(String)
    reasoning = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    state_snapshot = Column(JSON, nullable=True)

# Database setup
engine = None
SessionLocal = None

def init_db():
    """Initialize database connection and create tables"""
    global engine, SessionLocal
    
    db_url = os.getenv("DATABASE_URL", "sqlite:///./cerina_foundry.db")
    
    # Handle SQLite path
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
        )
    else:
        engine = create_engine(db_url)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine, SessionLocal

def get_db_session():
    """Get database session"""
    if SessionLocal is None:
        init_db()
    return SessionLocal()

