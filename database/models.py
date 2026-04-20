from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
import os

Base = declarative_base()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "doomcop.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="Study Session")
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)
    total_seconds = Column(Float, default=0)
    focus_seconds = Column(Float, default=0)
    doomscroll_seconds = Column(Float, default=0)
    doomscroll_count = Column(Integer, default=0)
    focus_score = Column(Float, default=100.0)
    roast_level = Column(String, default="mild")

    events = relationship("DoomscrollEvent", back_populates="session", cascade="all, delete-orphan")


class DoomscrollEvent(Base):
    __tablename__ = "doomscroll_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    triggered_at = Column(DateTime)
    duration_seconds = Column(Float, default=0)
    video_played = Column(String, nullable=True)

    session = relationship("Session", back_populates="events")


def init_db():
    Base.metadata.create_all(engine)
