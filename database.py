import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Đọc các biến từ file .env
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

# Xử lý URL encode cho username/password nếu cần
if MONGO_URL and "@" in MONGO_URL and "://" in MONGO_URL:
    try:
        protocol, rest = MONGO_URL.split("://", 1)
        if "@" in rest:
            auth_part, host_part = rest.split("@", 1)
            if ":" in auth_part:
                username, password = auth_part.split(":", 1)
                username_encoded = quote_plus(username)
                password_encoded = quote_plus(password)
                MONGO_URL = f"{protocol}://{username_encoded}:{password_encoded}@{host_part}"
    except:
        pass  # Sử dụng URL gốc nếu parse lỗi

# Tạo kết nối
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

print(f"Kết nối tới MongoDB: {DB_NAME}")