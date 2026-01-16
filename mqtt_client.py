from fastapi_mqtt import FastMQTT, MQTTConfig
import os
from dotenv import load_dotenv
import ssl
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

logger.info("=== MQTT Configuration ===")
logger.info(f"MQTT_HOST: {os.getenv('MQTT_HOST')}")
logger.info(f"MQTT_PORT: {os.getenv('MQTT_PORT')}")
logger.info(f"MQTT_USER: {os.getenv('MQTT_USER')}")

# Cấu hình MQTT
mqtt_config = MQTTConfig(
    host = os.getenv("MQTT_HOST"),
    port = int(os.getenv("MQTT_PORT")),
    username = os.getenv("MQTT_USER"),
    password = os.getenv("MQTT_PASSWORD"),
    keepalive = 60,
    ssl = ssl.create_default_context()
)

logger.info("Creating MQTT client...")
# Khởi tạo đối tượng MQTT
mqtt = FastMQTT(config=mqtt_config)
logger.info("MQTT client created successfully")