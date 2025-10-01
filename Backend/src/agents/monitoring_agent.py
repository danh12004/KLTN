import requests
import uuid
import os
import shutil
from werkzeug.utils import secure_filename
from datetime import datetime
from src.utils.config import CONFIG

class EnvironmentalMonitoringAgent:
    def __init__(self, decision_agent, image_agent, storage_folder):
        self.decision_agent = decision_agent
        self.image_agent = image_agent
        self.storage_folder = storage_folder
        self.mock_api_url = "https://68a96612b115e67576eb0cec.mockapi.io/image"

        if not os.path.exists(self.storage_folder):
            os.makedirs(self.storage_folder)
            print(f"Đã tạo thư mục lưu trữ tại: {self.storage_folder}")

    def check_risk_for_farmer(self, user, iot_data=None):
        """
        Kiểm tra rủi ro môi trường và chạy phân tích cho MỘT nông dân cụ thể.
        """
        farm = user.farms.first()
        if not farm:
            print(f"[AGENT GIÁM SÁT] Bỏ qua User ID {user.id} vì chưa có thông tin nông trại.")
            return

        farmer_id = user.id
        province = farm.province
        
        print(f"[{datetime.now()}] [AGENT GIÁM SÁT] Đang kiểm tra rủi ro cho nông hộ {farmer_id} tại {province}...")
        
        self.run_single_automated_analysis(farmer_id, farm, iot_data=iot_data, is_scheduled=True)

    def run_single_automated_analysis(self, farmer_id: str, iot_data=None, is_scheduled: bool = False):
        log_prefix = "[AUTO-ANALYSIS-SCHEDULED]" if is_scheduled else "[AUTO-ANALYSIS-MANUAL]"
        print(f"{log_prefix} Bắt đầu phân tích cho nông hộ {farmer_id}.")
        
        image_path = None
        try:
            print(f"{log_prefix} Đang lấy link ảnh từ {self.mock_api_url}...")
            api_response = requests.get(self.mock_api_url)
            api_response.raise_for_status()
            image_url = api_response.json()[0]['image']
            print(f"{log_prefix} Lấy được link ảnh: {image_url}")

            with requests.get(image_url, stream=True) as r:
                r.raise_for_status()
                image_bytes = r.content
            print(f"{log_prefix} Đã tải ảnh vào bộ nhớ.")

            detected_disease = self.image_agent.analyze_image(image_bytes)

            if "error" in detected_disease:
                print(f"{log_prefix} Lỗi từ agent nhận diện ảnh. Dừng lại.")
                return {"error": "Không thể phân tích được hình ảnh."}
            
            print(f"{log_prefix} Phát hiện '{detected_disease}'. Đang tạo kế hoạch...")

            if detected_disease in CONFIG.CLASS_NAMES:
                class_folder = os.path.join(self.storage_folder, detected_disease)
                os.makedirs(class_folder, exist_ok=True)
            else:
                class_folder = os.path.join(self.storage_folder, "unknown")
                os.makedirs(class_folder, exist_ok=True)

            image_filename = image_url.split('/')[-1]
            unique_filename = f"{uuid.uuid4().hex}_{secure_filename(image_filename)}"
            image_path = os.path.join(class_folder, unique_filename)

            with open(image_path, 'wb') as f:
                f.write(image_bytes)
            print(f"{log_prefix} Đã lưu ảnh tại: {image_path}")

            print(f"{log_prefix} Đang tạo kế hoạch...")
            plan = self.decision_agent.create_treatment_plan(
                detected_disease, 
                farmer_id,
                image_path_to_save=image_path,
                iot_data=iot_data
            )
            
            if is_scheduled:
                if "error" in plan:
                    print(f"{log_prefix} Lỗi khi tạo kế hoạch cho {farmer_id}: {plan['error']}")
                else:
                    print(f"{log_prefix} Đã tạo kế hoạch mới cho {farmer_id}. Hệ thống sẽ gửi thông báo (mô phỏng).")
                return 
            
            return plan

        except requests.exceptions.RequestException as e:
            print(f"{log_prefix} Lỗi khi gọi Mock API: {e}")
            return {"error": "Không thể lấy được ảnh từ hệ thống drone."}
        except Exception as e:
            print(f"{log_prefix} Lỗi không xác định: {e}")
            return {"error": "Đã có lỗi không xác định xảy ra trên server."}
