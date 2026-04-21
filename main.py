from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import models
import schemas
import security
from database import engine, get_db
from datetime import timedelta, date
import uuid
import asyncio
from typing import List

# 啟動時，自動在資料庫中建立我們在 models.py 定義好的所有資料表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wisemeal Clone API", description="類似 Wisemeal 的健康飲食 APP 後端")

# 設定 CORS (跨來源資源共用)，讓前端網頁可以合法呼叫後端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開發階段允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

@app.post("/api/auth/register", response_model=schemas.User, tags=["Authentication"])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="這個 Email 已經被註冊過了")
    
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(email=user.email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", response_model=schemas.Token, tags=["Authentication"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email 或密碼錯誤")
    
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=schemas.User, tags=["Users"])
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    """
    獲取當前登入者的基本資訊。
    需要有效的 JWT Token 進行驗證。
    """
    return current_user

@app.put("/api/users/me/profile", response_model=schemas.UserProfile, tags=["Users"])
def update_user_profile(
    profile_data: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    建立或更新當前登入者的個人檔案（身高、體重、目標等）。
    如果個人檔案不存在，則會建立一個新的。
    """
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    
    update_data = profile_data.dict(exclude_unset=True)

    if profile:
        for key, value in update_data.items():
            setattr(profile, key, value)
    else:
        profile = models.UserProfile(**update_data, user_id=current_user.id)
        db.add(profile)
        
    # 自動計算 TDEE 與目標熱量
    if profile.birth_date and profile.current_weight_kg and profile.height_cm and profile.gender and profile.activity_level and profile.target_date and profile.target_weight_kg:
        today = date.today()
        age = today.year - profile.birth_date.year - ((today.month, today.day) < (profile.birth_date.month, profile.birth_date.day))
        
        # BMR 計算 (Mifflin-St Jeor 公式)
        if profile.gender == 'male':
            bmr = (10 * profile.current_weight_kg) + (6.25 * profile.height_cm) - (5 * age) + 5
        else:
            bmr = (10 * profile.current_weight_kg) + (6.25 * profile.height_cm) - (5 * age) - 161
            
        # TDEE 計算 (活動量乘數)
        activity_multipliers = {'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55, 'active': 1.725, 'very_active': 1.9}
        tdee = bmr * activity_multipliers.get(profile.activity_level, 1.2)
        
        # 根據目標日期計算熱量缺口
        days_to_target = (profile.target_date - today).days
        if days_to_target > 0:
            weight_diff = profile.current_weight_kg - profile.target_weight_kg # 正數代表要減重
            # 1公斤體重約等於 7700 大卡
            daily_calorie_diff = (weight_diff * 7700) / days_to_target
            target = tdee - daily_calorie_diff
            
            # 健康安全底線保護：女性不低於 1200，男性不低於 1500
            min_calories = 1500 if profile.gender == 'male' else 1200
            target = max(target, min_calories)
        else:
            target = tdee        # 維持：吃 TDEE 的熱量
            
        profile.daily_calorie_target = int(target)

    db.commit()
    db.refresh(profile)
    return profile

@app.get("/api/entries/{entry_date}", response_model=schemas.DailyEntry, tags=["Diet Log"])
def get_or_create_daily_entry(
    entry_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    獲取使用者指定日期的飲食日誌。
    如果該日期還沒有日誌，系統會自動建立一個空的日誌。
    """
    entry = db.query(models.DailyEntry).filter(
        models.DailyEntry.user_id == current_user.id,
        models.DailyEntry.entry_date == entry_date
    ).first()

    if not entry:
        # 獲取使用者的專屬目標熱量
        profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
        target_cal = profile.daily_calorie_target if profile else None
        entry = models.DailyEntry(user_id=current_user.id, entry_date=entry_date, target_calories=target_cal)
        db.add(entry)
        db.commit()
        db.refresh(entry)

    return entry

@app.post("/api/entries/{entry_date}/food-items", response_model=schemas.FoodLogItem, tags=["Diet Log"])
def add_food_log_item(
    entry_date: date,
    item_data: schemas.FoodLogItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    在指定日期新增一筆食物紀錄 (例如：早餐吃了一顆蘋果 50 大卡)。
    """
    # 確保該日期的日誌存在
    entry = get_or_create_daily_entry(entry_date=entry_date, db=db, current_user=current_user)

    new_item = models.FoodLogItem(**item_data.dict(), entry_id=entry.id)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.delete("/api/food-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Diet Log"])
def delete_food_log_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    刪除一筆食物紀錄。只能刪除屬於自己的紀錄。
    """
    item = db.query(models.FoodLogItem).join(models.DailyEntry).filter(
        models.FoodLogItem.id == item_id,
        models.DailyEntry.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="找不到該食物紀錄或您沒有權限刪除")

    db.delete(item)
    db.commit()
    return None

@app.post("/api/ai/analyze-food-image", response_model=schemas.FoodAnalysisResponse, tags=["AI Features"])
async def analyze_food_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    上傳食物照片，透過 AI 辨識食物種類與營養成分。
    (目前為模擬功能，確認架構無誤後可串接真實的 Gemini/OpenAI API)
    """
    # 1. 讀取使用者上傳的圖片內容
    image_bytes = await file.read()
    
    # 2. 模擬網路傳輸與 AI 思考的等待時間 (2秒)
    await asyncio.sleep(2)
    
    # 3. TODO: 未來這裡將呼叫真實的 AI 視覺模型進行分析
    # 這裡我們先回傳一個模擬的完美辨識結果
    return schemas.FoodAnalysisResponse(
        food_name="照燒烤雞腿便當 (AI 辨識測試)",
        calories=680,
        protein=32.5,
        carbs=75.0,
        fat=22.0,
        confidence="high"
    )

@app.get("/api/dashboard/{entry_date}", response_model=schemas.DashboardSummary, tags=["Dashboard"])
def get_dashboard_summary(
    entry_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    獲取指定日期的儀表板數據總結 (總熱量與三大營養素加總)
    """
    entry = db.query(models.DailyEntry).filter(
        models.DailyEntry.user_id == current_user.id,
        models.DailyEntry.entry_date == entry_date
    ).first()

    summary = schemas.DashboardSummary(
        entry_date=entry_date, total_calories=0, target_calories=None,
        total_protein=0.0, total_carbs=0.0, total_fat=0.0
    )

    if entry:
        summary.target_calories = entry.target_calories
        for item in entry.food_items:
            summary.total_calories += item.calories
            summary.total_protein += (item.protein or 0.0)
            summary.total_carbs += (item.carbs or 0.0)
            summary.total_fat += (item.fat or 0.0)
            
    return summary

@app.post("/api/metrics", response_model=schemas.BodyMetricLog, tags=["Metrics"])
def add_body_metric(
    metric_data: schemas.BodyMetricLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """記錄每日身體數據，並同步更新個人檔案的目前體重"""
    new_metric = models.BodyMetricLog(**metric_data.dict(), user_id=current_user.id)
    db.add(new_metric)
    
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if profile:
        profile.current_weight_kg = metric_data.weight_kg
        
    db.commit()
    db.refresh(new_metric)
    return new_metric

@app.get("/api/metrics", response_model=List[schemas.BodyMetricLog], tags=["Metrics"])
def get_body_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """獲取歷史身體數據紀錄"""
    return db.query(models.BodyMetricLog).filter(models.BodyMetricLog.user_id == current_user.id).order_by(models.BodyMetricLog.record_date.desc()).all()

@app.post("/api/workouts", response_model=schemas.WorkoutLog, tags=["Workouts"])
def add_workout_log(
    workout_data: schemas.WorkoutLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    new_workout = models.WorkoutLog(**workout_data.dict(), user_id=current_user.id)
    db.add(new_workout)
    db.commit()
    db.refresh(new_workout)
    return new_workout