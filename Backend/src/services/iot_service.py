import os
import json
import random
from datetime import datetime

class IoTService:
    def __init__(self, save_path="D:\Final_Project\KLTN\Backend\data\clean_data"):
        self.save_path = save_path
        os.makedirs(self.save_path, exist_ok=True)

    def generate_fake_data(self, farm_id: int):
        return {    
            "farm_id": farm_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": round(random.uniform(22, 35), 1),
            "humidity": round(random.uniform(60, 95), 1),
            "soil_moisture": round(random.uniform(20, 60), 1),
            "soil_ph": round(random.uniform(5.0, 7.5), 2),
            "ec": round(random.uniform(0.5, 2.5), 2),
            "light": random.randint(200, 1000)
        }

    def save_to_json(self, farm_id: int, iot_data: dict):
        file_path = os.path.join(self.save_path, f"iot_farm.json")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(iot_data, f, indent=4, ensure_ascii=False)

        print(f"[IOT] Đã lưu dữ liệu mới vào {file_path}")

    def load_from_json(self, farm_id: int) -> dict:
        file_path = os.path.join(self.save_path, f"iot_farm.json")
        if not os.path.exists(file_path):
            print(f"[IOT] Chưa có dữ liệu IoT cho farm {farm_id}")
            return {}
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
