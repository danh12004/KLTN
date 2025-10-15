import json
import pandas as pd
from src.logging.logger import logger

class DataLoader:
    """
    Lớp tiện ích để tải các nguồn dữ liệu ban đầu như weather, knowledge base.
    """
    def __init__(self, weather_path, knowledge_base_path, farmers_path):
        self.weather_path = weather_path
        self.knowledge_base_path = knowledge_base_path
        self.farmers_path = farmers_path

    def load_all_data(self):
        """Tải tất cả dữ liệu từ các đường dẫn đã được cung cấp."""
        logger.info("Bắt đầu quá trình tải dữ liệu (weather, knowledge base, farmers)...")
        try:
            weather_df = pd.read_csv(self.weather_path)
            weather_df['date'] = pd.to_datetime(weather_df['date'])

            with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                knowledge_base = json.load(f)

            with open(self.farmers_path, 'r', encoding='utf-8') as f:
                farmers_data = json.load(f)

            logger.info("Tải tất cả dữ liệu thành công!")
            return {
                "weather": weather_df,
                "knowledge_base": knowledge_base,
                "farmers": farmers_data
            }
        except FileNotFoundError as e:
            logger.error(f"Lỗi không tìm thấy tệp tin cần thiết: {e}")
            return None
        except Exception as e:
            logger.error(f"Đã xảy ra lỗi không xác định khi tải dữ liệu: {e}")
            return None
