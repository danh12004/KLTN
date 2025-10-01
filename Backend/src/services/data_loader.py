import json
import pandas as pd

class DataLoader:
    def __init__(self, weather_path, knowledge_base_path, farmers_path):
        self.weather_path = weather_path
        self.knowledge_base_path = knowledge_base_path
        self.farmers_path = farmers_path

    def load_all_data(self):
        print("Đang tải dữ liệu...")
        try:
            weather_df = pd.read_csv(self.weather_path)
            weather_df['date'] = pd.to_datetime(weather_df['date'])

            with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                knowledge_base = json.load(f)

            with open(self.farmers_path, 'r', encoding='utf-8') as f:
                farmers_data = json.load(f)

            print("Tải dữ liệu thành công!")
            return {
                "weather": weather_df,
                "knowledge_base": knowledge_base,
                "farmers": farmers_data
            }
        except FileNotFoundError as e:
            print(f"Lỗi: Không tìm thấy tệp tin - {e}")
            return None
        except Exception as e:
            print(f"Đã xảy ra lỗi khi tải dữ liệu: {e}")
            return None