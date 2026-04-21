import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    # 使用通用的 UUID 類型，並移除 as_uuid=True 以相容 SQLite
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯設定
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    daily_entries = relationship("DailyEntry", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    user_id = Column(UUID, ForeignKey("users.id"), primary_key=True)
    nickname = Column(String(50))
    gender = Column(String(10))
    birth_date = Column(Date)
    height_cm = Column(Float)
    current_weight_kg = Column(Float)
    activity_level = Column(String(20))
    goal = Column(String(20))
    target_weight_kg = Column(Float)
    target_date = Column(Date)
    daily_calorie_target = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")

class DailyEntry(Base):
    __tablename__ = "daily_entries"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    entry_date = Column(Date, nullable=False)
    target_calories = Column(Integer)
    target_protein = Column(Float)
    target_carbs = Column(Float)
    target_fat = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="daily_entries")
    food_items = relationship("FoodLogItem", back_populates="entry", cascade="all, delete-orphan")

class FoodLogItem(Base):
    __tablename__ = "food_log_items"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID, ForeignKey("daily_entries.id"), nullable=False)
    food_name = Column(String(100), nullable=False)
    meal_type = Column(String(20), nullable=False) # e.g., breakfast, lunch, dinner, snack
    calories = Column(Integer, nullable=False)
    protein = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)
    logged_at = Column(DateTime, default=datetime.utcnow)

    entry = relationship("DailyEntry", back_populates="food_items")

class BodyMetricLog(Base):
    __tablename__ = "body_metric_logs"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    record_date = Column(Date, nullable=False)
    weight_kg = Column(Float, nullable=False)
    body_fat_percent = Column(Float)
    muscle_mass_kg = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkoutLog(Base):
    __tablename__ = "workout_logs"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    record_date = Column(Date, nullable=False)
    body_part = Column(String(50)) # 訓練部位
    cardio_minutes = Column(Integer, default=0) # 有氧時間
    created_at = Column(DateTime, default=datetime.utcnow)