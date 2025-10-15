import os
import io
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.efficientnet import preprocess_input as efficientnet_preprocess
from PIL import Image
from typing import Union, Dict
from src.logging.logger import logger

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

class ImageRecognitionAgent:
    def __init__(self, model_path: str, class_names: list, target_size: tuple = (224, 224)):
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