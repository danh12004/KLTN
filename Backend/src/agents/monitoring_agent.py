import requests
import uuid
import os
import io
from PIL import Image
import imagehash
from src.logging.logger import logger

class EnvironmentalMonitoringAgent:
    """
    Agent giám sát môi trường, chịu trách nhiệm phân tích hình ảnh tự động
    và kiểm tra các rủi ro tiềm ẩn cho nông trại.
    """
    def __init__(self, treatment_agent, image_agent, user_repo, storage_folder):
        self.treatment_agent = treatment_agent
        self.image_agent = image_agent
        self.user_repo = user_repo
        self.storage_folder = storage_folder
        self.mock_api_url = "https://68a96612b115e67576eb0cec.mockapi.io/image"
        
        os.makedirs(self.storage_folder, exist_ok=True)
        logger.info(f"Thư mục lưu trữ ảnh giám sát được đảm bảo tồn tại tại: {self.storage_folder}")

    def check_risk_for_farmer(self, user, iot_data=None):
        """
        Kiểm tra rủi ro và chạy phân tích cho MỘT nông dân cụ thể.
        Đây là hàm được gọi bởi scheduler (tác vụ nền).
        """
        farm = user.farms.first()
        if not farm:
            logger.warning(f"Bỏ qua User ID {user.id} vì chưa có thông tin nông trại.")
            return

        farmer_id = user.id
        logger.info(f"Bắt đầu kiểm tra rủi ro định kỳ cho nông hộ {farmer_id} tại {farm.province}...")
        
        self.run_single_automated_analysis(farmer_id, iot_data=iot_data, is_scheduled=True)

    def run_single_automated_analysis(self, farmer_id: str, iot_data=None, is_scheduled: bool = False):
        """
        Thực hiện một quy trình phân tích tự động hoàn chỉnh, bao gồm kiểm tra trùng lặp ảnh.
        """
        log_prefix = "[GIÁM SÁT ĐỊNH KỲ]" if is_scheduled else "[PHÂN TÍCH THỦ CÔNG]"
        logger.info(f"{log_prefix} Bắt đầu phân tích cho nông hộ {farmer_id}.")
        
        try:
            logger.info(f"{log_prefix} Đang lấy link ảnh từ API giám sát...")
            api_response = requests.get(self.mock_api_url)
            api_response.raise_for_status()
            image_url = api_response.json()[0]['image']
            logger.info(f"{log_prefix} Lấy được link ảnh: {image_url}")

            with requests.get(image_url, stream=True) as r:
                r.raise_for_status()
                image_bytes = r.content
            logger.info(f"{log_prefix} Đã tải ảnh thành công vào bộ nhớ.")

            detection_result = self.image_agent.analyze_image(image_bytes)

            if isinstance(detection_result, dict) and "error" in detection_result:
                logger.error(f"{log_prefix} Lỗi từ agent nhận diện ảnh: {detection_result['error']}. Dừng lại.")
                return {"error": "Không thể phân tích được hình ảnh."}

            if not isinstance(detection_result, str):
                error_detail = f"Dữ liệu nhận được: {str(detection_result)[:500]}..."
                logger.error(f"{log_prefix} Lỗi: Agent nhận diện ảnh trả về định dạng không hợp lệ. {error_detail}")
                return {"error": "Lỗi hệ thống: Agent nhận diện ảnh trả về định dạng không mong muốn."}
            
            detected_disease_name = detection_result
            logger.info(f"{log_prefix} Kết quả nhận diện: '{detected_disease_name}'.")
            
            image_path_to_save = None
            is_duplicate = False
            try:
                pil_image = Image.open(io.BytesIO(image_bytes))
                img_hash = imagehash.phash(pil_image)
                image_extension = ".jpg"
                unique_filename = f"{img_hash}{image_extension}"

                class_folder = os.path.join(self.storage_folder, detected_disease_name)
                os.makedirs(class_folder, exist_ok=True)
                image_path_to_save = os.path.join(class_folder, unique_filename)

                if os.path.exists(image_path_to_save):
                    logger.info(f"{log_prefix} Ảnh trùng lặp đã được phát hiện (hash: {img_hash}). Bỏ qua việc lưu ảnh mới.")
                    is_duplicate = True
                else:
                    pil_image.save(image_path_to_save)
                    logger.info(f"{log_prefix} Đã lưu ảnh mới tại: {image_path_to_save}")

            except Exception as e:
                logger.error(f"{log_prefix} Lỗi trong quá trình hashing hoặc lưu ảnh: {e}")
                return {"error": "Lỗi khi xử lý file ảnh."}

            if detected_disease_name == 'healthy':
                logger.info(f"{log_prefix} Cây trồng được xác định là khỏe mạnh. Không cần tạo kế hoạch điều trị.")
                if is_scheduled:
                    return
                else:
                    return {"message": "Phân tích hoàn tất. Cây trồng được xác định là khỏe mạnh.", "detection": "healthy", "is_duplicate": is_duplicate}

            logger.info(f"{log_prefix} Chuyển thông tin cho TreatmentAgent để tạo kế hoạch...")
            plan_result = self.treatment_agent.create_treatment_plan(
                detected_disease_name, 
                farmer_id,
                image_path_to_save=image_path_to_save,
                iot_data=iot_data
            )
            
            if is_scheduled:
                if "error" in plan_result:
                    logger.error(f"{log_prefix} Lỗi khi tạo kế hoạch cho {farmer_id}: {plan_result['error']}")
                else:
                    logger.info(f"{log_prefix} Đã tạo và lưu kế hoạch mới cho {farmer_id} thành công.")
                return
            
            if isinstance(plan_result, dict):
                plan_result['is_duplicate'] = is_duplicate
            
            return plan_result

        except requests.exceptions.RequestException as e:
            logger.error(f"{log_prefix} Lỗi khi gọi API giám sát: {e}")
            return {"error": "Không thể lấy được ảnh từ hệ thống drone/camera."}
        except Exception:
            logger.exception(f"Lỗi không xác định trong quá trình phân tích cho nông hộ {farmer_id}.")
            return {"error": "Lỗi không xác định trong quá trình phân tích."}
