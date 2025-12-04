import os
import io
import numpy as np
import requests
from PIL import Image
import imagehash
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.efficientnet import preprocess_input as efficientnet_preprocess
from PIL import Image
from typing import Union, Dict
from src.logging.logger import logger

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

class ImageRecognitionAgent:
    def __init__(self, model_path: str, class_names: list, storage_folder, target_size: tuple = (224, 224)):
        """
        Khởi tạo Agent nhận diện ảnh.

        Args:
            model_path (str): Đường dẫn đến file model .keras.
            class_names (list): Danh sách tên các lớp (bệnh) theo đúng thứ tự mà model đã được huấn luyện.
            target_size (tuple): Kích thước ảnh đầu vào cho model.
        """
        if not model_path or not os.path.exists(model_path):
            error_msg = f"Không tìm thấy file model tại '{model_path}'. Vui lòng kiểm tra lại cấu hình."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        logger.info(f"Đang tải model nhận diện ảnh từ: {model_path}")
        self.model = load_model(model_path)
        self.class_names = class_names
        self.target_size = target_size
        self.storage_folder = storage_folder
        logger.info("Tải model nhận diện ảnh thành công!")


    def _preprocess_image(self, pil_image: Image.Image) -> np.ndarray:
        """Tiền xử lý ảnh PIL để phù hợp với đầu vào của model EfficientNet."""
        img = pil_image.convert("RGB")
        img = img.resize(self.target_size)
        img_array = image.img_to_array(img)
        img_array = efficientnet_preprocess(img_array)
        img_array = np.expand_dims(img_array, axis=0)
        return img_array

    def analyze_image(self, image_input: Union[str, bytes]) -> Union[str, Dict[str, str]]:
        """
        Phân tích một ảnh để nhận diện bệnh.

        Args:
            image_input (Union[str, bytes]): Đầu vào có thể là đường dẫn file (str) hoặc dữ liệu ảnh (bytes).

        Returns:
            Union[str, Dict[str, str]]: Trả về tên bệnh (str) nếu thành công,
                                         hoặc một dictionary chứa lỗi (Dict) nếu thất bại.
        """
        logger.info("Bắt đầu phân tích ảnh...")
        try:
            pil_img = None
            if isinstance(image_input, str):
                pil_img = Image.open(image_input)
            elif isinstance(image_input, bytes):
                pil_img = Image.open(io.BytesIO(image_input))
            else:
                raise TypeError("Đầu vào của ảnh phải là đường dẫn file (str) hoặc dữ liệu (bytes).")

            img_array = self._preprocess_image(pil_img)

        except Exception as e:
            error_message = f"Lỗi khi đọc hoặc xử lý ảnh: {e}"
            logger.error(error_message)
            return {"error": error_message}

        try:
            preds = self.model.predict(img_array, verbose=0)[0]
            predicted_index = np.argmax(preds)
            disease_name = self.class_names[predicted_index]
            confidence = float(preds[predicted_index]) * 100

            logger.info(f"Kết quả nhận diện: '{disease_name}' (Độ tin cậy: {confidence:.2f}%)")
            return disease_name

        except Exception as e:
            error_message = f"Lỗi trong quá trình dự đoán của model: {e}"
            logger.error(error_message)
            return {"error": error_message}
        
    def detect_image(self, farmer_id: str, image_url: str):
        logger.info("Bắt đầu nhận diện hình ảnh!!!")
        
        try:
            logger.info(f"Đang tải ảnh từ URL: {image_url}")
            with requests.get(image_url, stream=True) as r: 
                r.raise_for_status()
                image_bytes = r.content
            logger.info(f"Đã tải ảnh thành công vào bộ nhớ.")
            
            detection_result = self.analyze_image(image_bytes)
            
            if isinstance(detection_result, dict) and "error" in detection_result:
                logger.error(f"Lỗi từ nhận diện ảnh: {detection_result['error']}")
                return {"error": "Không thể phân tích được hình ảnh."}
        
            if not isinstance(detection_result, str):
                error_detail = f"Dữ liệu nhận được: {str(detection_result)[:500]}..."
                logger.error(f"Lỗi: Nhận diện ảnh trả về định dạng không hợp lệ. {error_detail}")
                return {"error": "Lỗi hệ thống: Nhận diện ảnh trả về định dạng không mong muốn."}
        
            logger.info(f"Kết quả nhận diện: '{detection_result}'.")
            
            image_path_to_save = None
            try:
                pil_image = Image.open(io.BytesIO(image_bytes))
                if pil_image.mode == 'RGBA':
                    background = Image.new("RGB", pil_image.size, (255, 255, 255)) 
                    background.paste(pil_image, mask=pil_image.split()[3]) 
                    pil_image = background 
                img_hash = imagehash.phash(pil_image)
                image_extension = ".jpg"
                unique_filename = f"{img_hash}{image_extension}"

                class_folder = os.path.join(self.storage_folder, detection_result)
                os.makedirs(class_folder, exist_ok=True)
                image_path_to_save = os.path.join(class_folder, unique_filename)

                if os.path.exists(image_path_to_save):
                    logger.info(f"Ảnh trùng lặp đã được phát hiện (hash: {img_hash}). Bỏ qua việc lưu ảnh mới.")
                else:
                    pil_image.save(image_path_to_save)
                    logger.info(f"Đã lưu ảnh mới tại: {image_path_to_save}")
            except Exception as e:
                logger.error(f"Lỗi trong quá trình hashing hoặc lưu ảnh: {e}")
                return {"error": "Lỗi khi xử lý file ảnh."}
            
            return {
                "detected_disease_name": detection_result,
                "image_path_to_save": image_path_to_save
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi tải ảnh từ URL: {image_url}. Chi tiết: {e}")
            return {"error": "Không thể tải được ảnh từ đường dẫn đã cung cấp."}
        except Exception:
            logger.exception(f"Lỗi không xác định trong quá trình phân tích cho nông hộ {farmer_id}.")
            return {"error": "Lỗi không xác định trong quá trình phân tích."}