import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import json
from sqlalchemy.inspection import inspect

class TrainingCourse(Base):
    __tablename__ = "training_courses"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    compiler = Column(String, default="python")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sections = relationship("TrainingSection", back_populates="course", cascade="all, delete-orphan", order_by="TrainingSection.order")

class TrainingSection(Base):
    __tablename__ = "training_sections"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String, ForeignKey("training_courses.id"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)
    course = relationship("TrainingCourse", back_populates="sections")
    lessons = relationship("Lesson", back_populates="section", cascade="all, delete-orphan", order_by="Lesson.order")

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    section_id = Column(String, ForeignKey("training_sections.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    starting_code = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    validation_criteria = Column(JSON, nullable=True)
    section = relationship("TrainingSection", back_populates="lessons")

    def to_dict(self):
        """Returns a dict representation of the model, excluding relationships."""
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}

    def json(self):
        """Returns a JSON string representation of the model for use in templates."""
        def default_serializer(o):
            import datetime
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()
            raise TypeError(f"Type {type(o)} not serializable")
        return json.dumps(self.to_dict(), default=default_serializer)

