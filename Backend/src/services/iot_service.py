import os
import pandas as pd
import json
import random
import requests
import time
from typing import Optional
from datetime import datetime, timedelta
from src.utils.config import CONFIG
from src.logging.logger import logger

# class IoTService:
#     """
#     Dịch vụ mô phỏng việc tạo, lưu và đọc dữ liệu từ các cảm biến IoT.
#     Tất cả dữ liệu được lưu trong một file JSON duy nhất.
#     """
#     def __init__(self):
#         self.save_path = os.path.join(CONFIG.IOT_FOLDER, "iot_data")
#         os.makedirs(self.save_path, exist_ok=True)
#         self.data_file = os.path.join(self.save_path, "all_iot_data.json")
#         logger.info(f"File lưu trữ dữ liệu IoT tập trung tại: {self.data_file}")

#     def _read_all_data(self) -> dict:
#         """Đọc toàn bộ dữ liệu từ file JSON. Trả về {} nếu file không tồn tại hoặc rỗng."""
#         try:
#             with open(self.data_file, "r", encoding="utf-8") as f:
#                 content = f.read()
#                 if not content:
#                     return {}
#                 return json.loads(content)
#         except (FileNotFoundError, json.JSONDecodeError):
#             return {}

#     def _write_all_data(self, data: dict):
#         """Ghi toàn bộ dữ liệu vào file JSON."""
#         try:
#             with open(self.data_file, "w", encoding="utf-8") as f:
#                 json.dump(data, f, indent=4, ensure_ascii=False)
#         except Exception as e:
#             logger.error(f"Không thể ghi vào file IoT {self.data_file}: {e}")

    # def generate_fake_data(self, farm_id: int) -> dict:
    #     """Tạo ra một bộ dữ liệu cảm biến giả cho một nông trại, mô phỏng giống cấu trúc Firebase."""
    #     timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
    #     env_data = {
    #         "time": timestamp,
    #         "temp": round(random.uniform(25.0, 36.5), 1),
    #         "hum": round(random.uniform(70.0, 95.0), 1),
    #         "soil": round(random.uniform(30.0, 75.0), 1),
    #         "ph": round(random.uniform(5.5, 7.0), 2),
    #         "lux": round(random.uniform(100.0, 800.0), 1),
    #         "wind": round(random.uniform(0.0, 5.0), 2),
    #         "wind_avg": round(random.uniform(0.0, 4.0), 2)
    #     }
        
    #     gps_data = {
    #         "lat": round(random.uniform(10.75, 10.80), 6),
    #         "lon": round(random.uniform(106.65, 106.70), 6),
    #         "alt": round(random.uniform(1.0, 5.0), 2),
    #         "fix": random.choice([1, 2]),
    #         "time": timestamp
    #     }

    #     mapped_data = {
    #         "farm_id": farm_id,
    #         "date_key": datetime.utcnow().strftime("%Y-%m-%d"),
    #         "timestamp_key": timestamp,
    #         "timestamp": timestamp,
    #         "temperature": env_data["temp"],
    #         "humidity": env_data["hum"],
    #         "soil_moisture": env_data["soil"],
    #         "soil_ph": env_data["ph"],
    #         "lux": env_data["lux"],
    #         "wind": env_data["wind"],
    #         "wind_avg": env_data["wind_avg"],
    #         "water_level": round(random.uniform(2.0, 10.0), 1),
    #         "gps": gps_data,
    #         "image_url": "https://res.cloudinary.com/dkh9kzdvt/image/upload/v1755933252/4_iqmqsg.jpg
    #     }

    #     logger.info(f"Tạo dữ liệu giả IoT cho farm {farm_id}: {mapped_data}")
    #     return mapped_data


#     def save_data(self, farm_id: int, iot_data: dict):
#         """Cập nhật dữ liệu cho một farm_id cụ thể và lưu lại toàn bộ file."""
#         all_data = self._read_all_data()
#         all_data[str(farm_id)] = iot_data
#         self._write_all_data(all_data)
#         logger.info(f"Đã cập nhật dữ liệu IoT cho farm {farm_id} trong file tập trung.")

#     def get_latest_data(self, farm_id: int) -> dict:
#         """Lấy dữ liệu mới nhất cho một farm từ file JSON tập trung."""
#         all_data = self._read_all_data()
#         farm_id_str = str(farm_id)

#         if farm_id_str in all_data:
#             return all_data[farm_id_str]
#         else:
#             logger.info(f"Chưa có dữ liệu cảm biến cho farm {farm_id}. Tạo dữ liệu mới.")
#             new_data = self.generate_fake_data(farm_id)
#             self.save_data(farm_id, new_data) 
#             return new_data

class IoTService:
    FIREBASE_URL = "https://rice-813b5-default-rtdb.asia-southeast1.firebasedatabase.app/feeds.json"
    
    def __init__(self):
        self.save_path = os.path.join(CONFIG.IOT_FOLDER, "iot_data")
        os.makedirs(self.save_path, exist_ok=True)
        self.data_file = os.path.join(self.save_path, "all_iot_data.json")
        logger.info(f"Dịch vụ IoT đã sẵn sàng, trỏ tới Firebase: {self.FIREBASE_URL}")
        
    def _fetch_latest_from_firebase(self, farm_id) -> Optional[dict]: 
        """Gọi API Firebase để lấy dữ liệu mới nhất."""
        try:
            logger.info("Bắt đầu lấy dữ liệu từ iot service")
            response = requests.get(self.FIREBASE_URL, timeout=10)
            response.raise_for_status()
            all_data = response.json()
            

            if not all_data:
                logger.warning("Firebase trả về dữ liệu rỗng.")
                return None
            
            latest_date_key = sorted(all_data.keys(), reverse=True)[0]
            latest_date_entry = all_data.get(latest_date_key, {})

            if not latest_date_entry:
                logger.warning(f"Không có entry con nào trong ngày {latest_date_key}.")
                return None
            
            latest_timestamp_key = sorted(latest_date_entry.keys(), reverse=True)[0]
            latest_entry = latest_date_entry.get(latest_timestamp_key, {})

            if not latest_entry:
                logger.warning("Không tìm thấy entry chi tiết mới nhất.")
                return None

            print("\n===== ENTRY MỚI NHẤT =====")

            env_data = latest_entry.get("env", {})
            gps_data = latest_entry.get("gps", {})
            img_data = latest_entry.get("image", {})

            mapped_data = {
                "farm_id": farm_id,
                "date_key": latest_date_key,
                "timestamp_key": latest_timestamp_key,
                "timestamp": env_data.get("time") or gps_data.get("time") or latest_timestamp_key,
                "temperature": env_data.get("temp"),
                "humidity": env_data.get("hum"),
                "soil_moisture": env_data.get("soil"),
                "soil_ph": env_data.get("ph"),
                "lux": env_data.get("lux"),
                "wind": env_data.get("wind"),
                "wind_avg": env_data.get("wind_avg"),
                "water_level": round(random.uniform(2.0, 10.0), 1),
                "gps": {
                    "lat": gps_data.get("lat"),
                    "lon": gps_data.get("lon"),
                    "alt": gps_data.get("alt"),
                    "fix": gps_data.get("fix"),
                    "time": gps_data.get("time")
                },
                "image_url": img_data.get("url"),
            }

            logger.info(f"Lấy thành công dữ liệu mới nhất: {latest_date_key} / {latest_timestamp_key}")
            return mapped_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi gọi API Firebase: {e}")
            return None
        except Exception as e:
            logger.error(f"Lỗi khi xử lý dữ liệu Firebase: {e}")
            return None

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
            
    def save_data(self, farm_id: int, iot_data: dict):
        """Cập nhật dữ liệu cho một farm_id cụ thể và lưu lại toàn bộ file."""
        all_data = self._read_all_data()
        all_data[str(farm_id)] = iot_data
        self._write_all_data(all_data)
        logger.info(f"Đã cập nhật dữ liệu IoT cho farm {farm_id} trong file tập trung.")

    def get_latest_data(self, farm_id: int) -> dict:
        logger.info(f"Chưa có dữ liệu cảm biến cho farm {farm_id}. Tạo dữ liệu mới.")
        new_data = self._fetch_latest_from_firebase(farm_id)
        self.save_data(farm_id, new_data) 
        return new_data
        
    def _read_all_entries(self) -> Optional[dict]:
        """Lấy tất cả các entry (date_key) từ Firebase để tổng hợp lịch sử."""
        try:
            response = requests.get(self.FIREBASE_URL, timeout=20) 
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi lấy toàn bộ dữ liệu từ Firebase: {e}")
            return None
        
    def get_hourly_data(self, farm_id: int, hours: int = 168) -> pd.DataFrame:
        """Lấy dữ liệu thô (theo giờ/phút) trong N giờ gần nhất."""
        all_feeds = self._read_all_entries()
        
        if not all_feeds:
            return pd.DataFrame()

        records = []
        for date_key, date_data in all_feeds.items():
            for timestamp_key, entry in date_data.items():
                env_data = entry.get("env", {})
                
                ts_str = env_data.get("time") or entry.get("timestamp")
                
                try:
                    ts = pd.to_datetime(ts_str, utc=True) if isinstance(ts_str, str) else None
                except:
                    continue 

                record = {
                    "timestamp": ts,
                    "temperature": env_data.get("temp"),
                    "humidity": env_data.get("hum"),
                    "soil_moisture": env_data.get("soil"),
                    "soil_ph": env_data.get("ph"),
                    "lux": env_data.get("lux"),
                    "wind": env_data.get("wind"),
                    "wind_avg": env_data.get("wind_avg"),
                    "water_level": entry.get("water_level", round(random.uniform(2.0, 10.0), 1)),
                }
                records.append(record)

        if not records:
            return pd.DataFrame()
        
        df_raw = pd.DataFrame(records)
        df_raw.set_index('timestamp', inplace=True)
        df_raw.dropna(subset=['temperature'], inplace=True) 

        df_raw = df_raw.sort_index()
        time_cutoff = df_raw.index.max() - pd.Timedelta(hours=hours)
        df_filtered = df_raw[df_raw.index >= time_cutoff]
        
        return df_filtered
    
    
    def _generate_fake_history(self, end_time: datetime, days: int = 5) -> pd.DataFrame:
        """
        Tạo dữ liệu lịch sử giả theo giờ cho N ngày trước end_time.
        Dữ liệu này sẽ được dùng để bổ sung cho dự báo.
        """
        records = []
        
        num_hours = days * 24
        
        start_time = end_time - timedelta(days=days)

        current_time = start_time
        while current_time < end_time:
            temp = round(random.uniform(25.0, 35.0) + (current_time.hour - 12) / 6, 1) # Giả lập ngày/đêm
            hum = round(random.uniform(70.0, 95.0) - (temp - 28) * 1.5, 1) 
            soil_moisture = round(random.uniform(20.0, 40.0) + random.uniform(-5, 5), 1)
            soil_ph = round(random.uniform(6.0, 7.0), 1)
            lux = round(random.uniform(100.0, 800.0) + current_time.hour * 500, 1) # Giả lập ánh sáng
            wind = round(random.uniform(0.0, 5.0), 1)
            wind_avg = round(wind * random.uniform(0.8, 1.2), 1)
            water_level = round(random.uniform(3.0, 8.0) + random.uniform(-1, 1), 1)

            record = {
                "timestamp": current_time,
                "temperature": temp,
                "humidity": hum,
                "soil_moisture": soil_moisture,
                "soil_ph": soil_ph,
                "lux": lux if current_time.hour > 6 and current_time.hour < 18 else round(random.uniform(0, 50), 1),
                "wind": wind,
                "wind_avg": wind_avg,
                "water_level": water_level,
            }
            records.append(record)
            
            current_time += timedelta(hours=1) 

        df_fake = pd.DataFrame(records)
        df_fake.set_index('timestamp', inplace=True)
        logger.info(f"Đã tạo {len(df_fake)} giờ dữ liệu giả (từ {df_fake.index.min()} đến {df_fake.index.max()}).")
        return df_fake[
            ["temperature", "humidity", "soil_moisture", "soil_ph", "lux", "wind", "wind_avg", "water_level"]
        ]
        
    def fetch_mock_image_data(session_id, lat, lon):
        logger.info(f"[SCHEDULER] Giả lập chờ ảnh mới về cho session {session_id} (30s)...")
        time.sleep(30) 
        
        MOCK_API_URL = "https://68a96612b115e67576eb0cec.mockapi.io/image"
        try:
            response = requests.get(MOCK_API_URL)
            response.raise_for_status() 
            image_data = response.json()
            logger.info(f"[SCHEDULER] Lấy thành công dữ liệu ảnh/IoT mock.")
            return {"status": "success", "image_data": image_data}
        except Exception as e:
            logger.error(f"[SCHEDULER] Lỗi khi lấy ảnh từ Mock API: {e}")
            return {"status": "error", "message": str(e)}    