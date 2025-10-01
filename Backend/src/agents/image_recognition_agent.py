import os
import io
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.efficientnet import preprocess_input as efficientnet_preprocess
from PIL import Image

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

class ImageRecognitionAgent:
    def __init__(self, model_path, class_names, target_size=(224, 224)):
        print("Đang tải model nhận diện ảnh...")
        self.model = load_model(model_path)
        self.class_names = class_names
        self.target_size = target_size
        print("Tải model nhận diện ảnh thành công!")

    def _preprocess_image(self, pil_image: Image.Image):
        img = pil_image.convert("RGB")
        img = img.resize(self.target_size)
        img_array = image.img_to_array(img)
        img_array = efficientnet_preprocess(img_array)
        img_array = np.expand_dims(img_array, axis=0)
        return img_array

    def analyze_image(self, image_input: str) -> str:
        print(f"\n[AGENT NHẬN DIỆN ẢNH] Đang phân tích ảnh'...")
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
            print(f"[AGENT NHẬN DIỆN ẢNH] Lỗi khi đọc hoặc xử lý ảnh: {e}")
            return "error_image_processing"

        preds = self.model.predict(img_array, verbose=0)[0]
        predicted_index = np.argmax(preds)
        disease_name = self.class_names[predicted_index]
        confidence = float(preds[predicted_index]) * 100

        print(f"[AGENT NHẬN DIỆN ẢNH] Kết quả: '{disease_name}' ({confidence:.2f}%)")
        return disease_name