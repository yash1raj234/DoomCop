from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from .models import Session, DoomscrollEvent, engine, init_db


def get_db():
    return DBSession(engine)


def create_session(name="Study Session"):
    init_db()
    db = get_db()
    session = Session(name=name, start_time=datetime.now())
    db.add(session)
    db.commit()
    db.refresh(session)
    session_id = session.id
    db.close()
    return session_id


def end_session(session_id, total_seconds, focus_seconds, doomscroll_seconds, doomscroll_count):
    db = get_db()
    session = db.query(Session).filter(Session.id == session_id).first()
    if session:
        session.end_time = datetime.now()
        session.total_seconds = total_seconds
        session.focus_seconds = focus_seconds
        session.doomscroll_seconds = doomscroll_seconds
        session.doomscroll_count = doomscroll_count
        if total_seconds > 0:
            session.focus_score = round((focus_seconds / total_seconds) * 100, 1)
        else:
            session.focus_score = 100.0
        if doomscroll_count == 0:
            session.roast_level = "mild"
        elif doomscroll_count <= 3:
            session.roast_level = "medium"
        else:
            session.roast_level = "savage"
        db.commit()
        result = {
            "id": session.id,
            "name": session.name,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "total_seconds": session.total_seconds,
            "focus_seconds": session.focus_seconds,
            "doomscroll_seconds": session.doomscroll_seconds,
            "doomscroll_count": session.doomscroll_count,
            "focus_score": session.focus_score,
            "roast_level": session.roast_level,
        }
        db.close()
        return result
    db.close()
    return None


def log_doomscroll_event(session_id, duration_seconds=0, video_played=None):
    db = get_db()
    event = DoomscrollEvent(
        session_id=session_id,
        triggered_at=datetime.now(),
        duration_seconds=duration_seconds,
        video_played=video_played,
    )
    db.add(event)
    db.commit()
    db.close()


def get_all_sessions():
    init_db()
    db = get_db()
    sessions = db.query(Session).order_by(Session.start_time.desc()).all()
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "name": s.name,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "total_seconds": s.total_seconds or 0,
            "focus_seconds": s.focus_seconds or 0,
            "doomscroll_seconds": s.doomscroll_seconds or 0,
            "doomscroll_count": s.doomscroll_count or 0,
            "focus_score": s.focus_score or 100.0,
        })
    db.close()
    return result


def get_total_stats():
    init_db()
    db = get_db()
    sessions = db.query(Session).filter(Session.end_time.isnot(None)).all()
    total_focus = sum(s.focus_seconds or 0 for s in sessions)
    total_sessions = len(sessions)
    total_caught = sum(s.doomscroll_count or 0 for s in sessions)
    total_doom_seconds = sum(s.doomscroll_seconds or 0 for s in sessions)
    db.close()
    return {
        "total_focus_seconds": total_focus,
        "total_sessions": total_sessions,
        "total_caught": total_caught,
        "total_doom_seconds": total_doom_seconds,
    }
