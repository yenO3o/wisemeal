from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 我們將使用 SQLite，它是一個免安裝的檔案型資料庫。
# 這行會告訴 SQLAlchemy 在專案目錄下建立一個名為 wisemeal.db 的檔案來儲存所有資料。
SQLALCHEMY_DATABASE_URL = "sqlite:///./wisemeal.db"

# 參數 connect_args={"check_same_thread": False} 是 SQLite 特有的設定，
# 為了讓 FastAPI 可以正常使用它。
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()