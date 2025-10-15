import os
import json
import random
from datetime import datetime
from src.utils.config import CONFIG
from src.logging.logger import logger

class IoTService:
    """
    Dịch vụ mô phỏng việc tạo, lưu và đọc dữ liệu từ các cảm biến IoT.
    Tất cả dữ liệu được lưu trong một file JSON duy nhất.
    """
    def __init__(self):
        self.save_path = os.path.join(CONFIG.IOT_FOLDER, "iot_data")
        os.makedirs(self.save_path, exist_ok=True)
        self.data_file = os.path.join(self.save_path, "all_iot_data.json")
        logger.info(f"File lưu trữ dữ liệu IoT tập trung tại: {self.data_file}")

    def _read_all_data(self) -> dict:
        """Đọc toàn bộ dữ liệu từ file JSON. Trả về {} nếu file không tồn tại hoặc rỗng."""
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content:
                    return {}
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_all_data(self, data: dict):
        """Ghi toàn bộ dữ liệu vào file JSON."""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Không thể ghi vào file IoT {self.data_file}: {e}")

    def generate_fake_data(self, farm_id: int) -> dict:
        """Tạo ra một bộ dữ liệu cảm biến giả cho một nông trại cụ thể."""
        return {
            "farm_id": farm_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "temperature": round(random.uniform(25.0, 36.5), 1),
            "humidity": round(random.uniform(70.0, 95.0), 1),
            "soil_moisture": round(random.uniform(30.0, 75.0), 1),
            "soil_ph": round(random.uniform(5.5, 7.0), 2),
            "water_level": round(random.uniform(2.0, 10.0), 1)
        }

    def save_data(self, farm_id: int, iot_data: dict):
        """Cập nhật dữ liệu cho một farm_id cụ thể và lưu lại toàn bộ file."""
        all_data = self._read_all_data()
        all_data[str(farm_id)] = iot_data
        self._write_all_data(all_data)
        logger.info(f"Đã cập nhật dữ liệu IoT cho farm {farm_id} trong file tập trung.")

    def get_latest_data(self, farm_id: int) -> dict:
        """Lấy dữ liệu mới nhất cho một farm từ file JSON tập trung."""
        all_data = self._read_all_data()
        farm_id_str = str(farm_id)

        if farm_id_str in all_data:
            return all_data[farm_id_str]
        else:
            logger.info(f"Chưa có dữ liệu cảm biến cho farm {farm_id}. Tạo dữ liệu mới.")
            new_data = self.generate_fake_data(farm_id)
            self.save_data(farm_id, new_data) 
            return new_data
