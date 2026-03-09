# database.py
# ────────────────────────────────────────────────────────────────
# Single file containing: connection, base, and all 8 SQLAlchemy models
# Optimized for Railway deployment (uses DATABASE_URL env var)
# ────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, Numeric, ForeignKey, DateTime, SmallInteger, Text, UniqueConstraint, func
from sqlalchemy.orm import sessionmaker, scoped_session, relationship, declarative_base

load_dotenv()  # Loads .env only for local dev; ignored on Railway

# ── Database URL ─────────────────────────────────────────────────
# Railway automatically sets DATABASE_URL when you add PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")

# Fallback for local development only (when running outside Railway)
if not DATABASE_URL:
    DATABASE_URL = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )

# Optional debug print (shows which URL is used - remove in production if desired)
print(f"Using DATABASE_URL: {DATABASE_URL[:60]}...")  # Shortened to hide credentials

engine = create_engine(DATABASE_URL, echo=False)  # Change to echo=True for SQL debug

SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()

# ── Model Definitions (8 tables) with relationships ──────────────

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    checklist_items = relationship("ChecklistItem", back_populates="category", cascade="all, delete-orphan")
    category_scores = relationship("CategoryScore", back_populates="category")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"))
    item_text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    category = relationship("Category", back_populates="checklist_items")
    feedback_violations = relationship("FeedbackViolation", back_populates="checklist_item")
    strike_events = relationship("StrikeEvent", back_populates="checklist_item")


class Labour(Base):
    __tablename__ = "labours"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)
    phone = Column(String(20))
    employee_code = Column(String(50), unique=True, nullable=True)
    joined_date = Column(Date, server_default=func.current_date())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    attendance_records = relationship("AttendanceRecord", back_populates="labour", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")
    created_at = Column(DateTime, server_default=func.now())


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True)
    labour_id = Column(Integer, ForeignKey("labours.id", ondelete="CASCADE"), nullable=False)
    record_date = Column(Date, nullable=False)
    status = Column(String(20))  # Present, Absent, Half Day
    advance_amount = Column(Numeric(10,2), default=0)
    total_points = Column(Integer, default=0)
    total_break_minutes = Column(Integer, default=0)
    frozen = Column(Boolean, default=False)
    current_break_start = Column(DateTime, nullable=True)  # Added for break tracking
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('labour_id', 'record_date', name='unique_labour_date'),
    )

    # Relationships
    labour = relationship("Labour", back_populates="attendance_records")
    category_scores = relationship("CategoryScore", back_populates="attendance_record", cascade="all, delete-orphan")
    feedback_violations = relationship("FeedbackViolation", back_populates="attendance_record", cascade="all, delete-orphan")
    strike_events = relationship("StrikeEvent", back_populates="attendance_record")


class CategoryScore(Base):
    __tablename__ = "category_scores"
    id = Column(Integer, primary_key=True)
    attendance_record_id = Column(Integer, ForeignKey("attendance_records.id", ondelete="CASCADE"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    score = Column(SmallInteger)  # -1, 0, 1
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    attendance_record = relationship("AttendanceRecord", back_populates="category_scores")
    category = relationship("Category", back_populates="category_scores")


class FeedbackViolation(Base):
    __tablename__ = "feedback_violations"
    id = Column(Integer, primary_key=True)
    attendance_record_id = Column(Integer, ForeignKey("attendance_records.id", ondelete="CASCADE"))
    labour_id = Column(Integer, ForeignKey("labours.id"))
    checklist_item_id = Column(Integer, ForeignKey("checklist_items.id"))
    violation_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    attendance_record = relationship("AttendanceRecord", back_populates="feedback_violations")
    labour = relationship("Labour")
    checklist_item = relationship("ChecklistItem", back_populates="feedback_violations")


class StrikeEvent(Base):
    __tablename__ = "strike_events"
    id = Column(Integer, primary_key=True)
    labour_id = Column(Integer, ForeignKey("labours.id", ondelete="CASCADE"))
    checklist_item_id = Column(Integer, ForeignKey("checklist_items.id"))
    record_date = Column(Date, nullable=False)
    strike_number = Column(Integer, nullable=False)
    attendance_record_id = Column(Integer, ForeignKey("attendance_records.id"))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    labour = relationship("Labour")
    checklist_item = relationship("ChecklistItem", back_populates="strike_events")
    attendance_record = relationship("AttendanceRecord", back_populates="strike_events")

# ── Helper function to create tables (call once) ──────────────────
def init_db():
    Base.metadata.create_all(bind=engine)

