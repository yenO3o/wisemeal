import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# Pydantic's orm_mode 會告訴 Pydantic 模型去讀取非 dict 的資料，
# 例如 ORM 模型 (我們在 models.py 中定義的 class)。
class Config:
    from_attributes = True

# ==================================
# FoodLogItem Schemas
# ==================================

class FoodLogItemBase(BaseModel):
    food_name: str = Field(..., max_length=100)
    meal_type: str = Field(..., max_length=20)
    calories: int = Field(..., gt=0)
    protein: float = Field(0.0, ge=0)
    carbs: float = Field(0.0, ge=0)
    fat: float = Field(0.0, ge=0)

class FoodLogItemCreate(FoodLogItemBase):
    pass

class FoodLogItem(FoodLogItemBase):
    id: uuid.UUID
    entry_id: uuid.UUID
    logged_at: datetime

    class Config(Config):
        pass

# ==================================
# DailyEntry Schemas
# ==================================

class DailyEntryBase(BaseModel):
    entry_date: date
    target_calories: Optional[int] = None
    target_protein: Optional[float] = None
    target_carbs: Optional[float] = None
    target_fat: Optional[float] = None

class DailyEntryCreate(DailyEntryBase):
    pass

class DailyEntry(DailyEntryBase):
    id: uuid.UUID
    user_id: uuid.UUID
    food_items: List[FoodLogItem] = []

    class Config(Config):
        pass

# ==================================
# UserProfile Schemas
# ==================================

class UserProfileBase(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    gender: Optional[str] = Field(None, max_length=10)
    birth_date: Optional[date] = None
    height_cm: Optional[float] = Field(None, gt=0)
    current_weight_kg: Optional[float] = Field(None, gt=0)
    activity_level: Optional[str] = Field(None, max_length=20)
    goal: Optional[str] = Field(None, max_length=20)
    target_weight_kg: Optional[float] = Field(None, gt=0)
    target_date: Optional[date] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfile(UserProfileBase):
    user_id: uuid.UUID
    daily_calorie_target: Optional[int] = None

    class Config(Config):
        pass

# ==================================
# User Schemas
# ==================================

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class User(UserBase):
    id: uuid.UUID
    created_at: datetime
    profile: Optional[UserProfile] = None

    class Config(Config):
        pass

# ==================================
# Token Schemas (for Authentication)
# ==================================

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# ==================================
# AI Feature Schemas
# ==================================

class FoodAnalysisResponse(BaseModel):
    food_name: str = Field(..., description="AI 辨識出的食物名稱")
    calories: int = Field(..., description="預估總熱量")
    protein: float = Field(..., description="預估蛋白質(g)")
    carbs: float = Field(..., description="預估碳水化合物(g)")
    fat: float = Field(..., description="預估脂肪(g)")
    confidence: str = Field(..., description="AI 辨識信心度 (high, medium, low)")

class DashboardSummary(BaseModel):
    entry_date: date
    total_calories: int
    target_calories: Optional[int] = None
    total_protein: float
    total_carbs: float
    total_fat: float

# ==================================
# Body Metric Schemas
# ==================================

class BodyMetricLogBase(BaseModel):
    record_date: date
    weight_kg: float = Field(..., gt=0)
    body_fat_percent: Optional[float] = Field(None, ge=0, le=100)
    muscle_mass_kg: Optional[float] = Field(None, ge=0)

class BodyMetricLogCreate(BodyMetricLogBase):
    pass

class BodyMetricLog(BodyMetricLogBase):
    id: uuid.UUID
    user_id: uuid.UUID

    class Config(Config):
        pass

# ==================================
# Workout Schemas
# ==================================

class WorkoutLogBase(BaseModel):
    record_date: date
    body_part: Optional[str] = None
    cardio_minutes: Optional[int] = 0

class WorkoutLogCreate(WorkoutLogBase):
    pass

class WorkoutLog(WorkoutLogBase):
    id: uuid.UUID
    user_id: uuid.UUID

    class Config(Config):
        pass