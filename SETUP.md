# 🔧 SETUP .env - Hướng dẫn Chi tiết

## 📋 Các biến cần thiết

Backend cần **4 biến bắt buộc**:

```
MONGO_URL     → Kết nối MongoDB
DB_NAME       → Tên database
MQTT_HOST     → Địa chỉ MQTT Broker
MQTT_PORT     → Cổng MQTT
MQTT_USER     → Username MQTT
MQTT_PASSWORD → Password MQTT
```

---

## 🗄️ MongoDB Setup

### Tùy chọn 1: Local MongoDB (Recommended for testing)

**Trên Windows:**
1. Download & install từ: https://www.mongodb.com/try/download/community
2. Sau khi install, MongoDB chạy trên `localhost:27017`

**File .env:**
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=smart_home_db
```

**Test kết nối:**
```bash
mongosh  # Nếu có mongosh CLI
```

---

### Tùy chọn 2: MongoDB Atlas (Cloud - Free)

**Bước 1:** Tạo tài khoản
- Vào: https://www.mongodb.com/cloud/atlas
- Sign up (hoặc login)

**Bước 2:** Tạo Cluster
- Click "Build a Cluster"
- Chọn "Free" tier
- Chọn region (e.g., Singapore, Tokyo)
- Click "Create Cluster"
- Chờ 2-3 phút cluster tạo xong

**Bước 3:** Lấy connection string
- Trong Atlas Dashboard, click "Connect"
- Chọn "Connect your application"
- Copy connection string (dạng: `mongodb+srv://...`)
- Thay `<password>` bằng password của user
- Thay `<username>` bằng username của user

**File .env:**
```
MONGO_URL=mongodb+srv://admin:password123@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DB_NAME=smart_home_db
```

**Lưu ý:**
- Password không được có các ký tự đặc biệt (hoặc URL encode)
- Phải whitelist IP của máy tính hoặc allow all IPs (0.0.0.0/0)

---

## 🔌 MQTT Broker Setup

### Tùy chọn 1: Local Mosquitto (Recommended for testing)

**Trên Windows:**
1. Download: https://mosquitto.org/download/
2. Install (chọn "Service" khi cài)
3. Mặc định chạy trên `localhost:1883`

**File .env:**
```
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USER=
MQTT_PASSWORD=
```

**Test kết nối:**
```bash
# Terminal 1: Subscribe
mosquitto_sub -h localhost -t "+/+" -v

# Terminal 2: Publish
mosquitto_pub -h localhost -t "room1/device" -m '{"device1":1}'
```

---

### Tùy chọn 2: HiveMQ Cloud (Free - Recommended)

**Bước 1:** Tạo tài khoản
- Vào: https://console.hivemq.cloud/
- Sign up

**Bước 2:** Tạo Cluster
- Click "Create New Cluster"
- Chọn "Serverless"
- Chọn region
- Click "Create"

**Bước 3:** Lấy credentials
- Cluster Details sẽ show:
  - **Host:** `xxxxx.s.eu.hivemq.cloud` (hoặc region khác)
  - **Port:** `8883` (TLS/SSL)
  - **Username/Password:** Set trong tab "Access Management"

**File .env:**
```
MQTT_HOST=xxxxx.s.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USER=your_username
MQTT_PASSWORD=your_password
```

---

## ✅ Complete .env Example (Local Testing)

```env
# MongoDB Local
MONGO_URL=mongodb://localhost:27017
DB_NAME=smart_home_db

# Mosquitto Local
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USER=
MQTT_PASSWORD=
```

**Chạy:**
```bash
# Terminal 1: Start MongoDB (nếu not service)
mongod

# Terminal 2: Start Mosquitto (nếu not service)
mosquitto

# Terminal 3: Start Backend
uvicorn main:app --reload
```

---

## ✅ Complete .env Example (Cloud Setup)

```env
# MongoDB Atlas
MONGO_URL=mongodb+srv://admin:pass123@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DB_NAME=smart_home_db

# HiveMQ Cloud
MQTT_HOST=xxxxx.s.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USER=your_username
MQTT_PASSWORD=your_password
```

**Chạy:**
```bash
uvicorn main:app --reload
# Tất cả cloud nên chạy tự động
```

---

## 🐛 Troubleshooting

| Lỗi | Giải pháp |
|-----|----------|
| `Connection refused: MongoDB` | MongoDB không chạy hoặc URL sai |
| `Failed to connect MQTT broker` | Mosquitto/HiveMQ không chạy hoặc credentials sai |
| `Connection timeout` | Firewall hoặc network issue |
| `Invalid connection string` | Check password có ký tự đặc biệt không |

---

## 🚀 Test sau khi setup

```bash
# Chạy backend
uvicorn main:app --reload

# Kiểm tra API
curl http://localhost:8000/docs

# Test tạo room
curl -X POST http://localhost:8000/rooms/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Phòng khách"}'
```

Nếu thành công sẽ trả về `roomId`.

---

**Chọn 1 trong 2 option cho mỗi service rồi setup .env là xong!** ✅
