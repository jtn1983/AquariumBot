# db.py

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey, Boolean, Time
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, backref
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()

class Aquarium(Base):
    __tablename__ = "aquariums"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    name = Column(String)
    type = Column(String)
    volume = Column(Float)
    measurements = relationship("Measurement", back_populates="aquarium")

class Measurement(Base):
    __tablename__ = "measurements"
    id = Column(Integer, primary_key=True)
    aquarium_id = Column(Integer, ForeignKey("aquariums.id"))
    param = Column(String)
    value = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    comment = Column(String, default="")
    aquarium = relationship("Aquarium", back_populates="measurements")


class ServiceTask(Base):
    __tablename__ = "service_tasks"
    id = Column(Integer, primary_key=True)
    aquarium_id = Column(Integer, ForeignKey("aquariums.id"))
    user_id = Column(Integer)
    name = Column(String)            # Название задачи (например, "Подменить воду")
    period_days = Column(Integer)    # Периодичность (раз в сколько дней)
    last_done = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    remind_time = Column(Time, nullable=True)
    next_run = Column(DateTime, nullable=True)

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    aquarium_id = Column(Integer, ForeignKey("aquariums.id"))
    user_id = Column(Integer)
    title = Column(String, nullable=True)
    text = Column(String)           # текст заметки
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    aquarium = relationship("Aquarium", backref="notes")
    
class NotePhoto(Base):
    __tablename__ = "note_photos"
    id = Column(Integer, primary_key=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    file_id = Column(String, nullable=False)
    caption = Column(String, nullable=True)

    note = relationship("Note", backref=backref("photos", cascade="all, delete-orphan"))

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)