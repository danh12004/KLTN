import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_latest_model_path(models_dir, prefix="efficientnet_model_v", ext=".keras"):
    all_models = [f for f in os.listdir(models_dir) if f.startswith(prefix) and f.endswith(ext)]
    if not all_models:
        return None
    latest_model = sorted(all_models, key=lambda x: int(x.split('_v')[-1].split('.')[0]))[-1]
    return os.path.join(models_dir, latest_model)

class AppConfig:
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a_default_secret_key_for_development")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "a_default_jwt_secret_key_for_development")
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("Lỗi: Biến môi trường DATABASE_URL chưa được thiết lập.")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    STORAGE_FOLDER = os.path.join(BASE_DIR, "data", "clean_data", "image_data", "storage")
    KNOWLEDGE_BASE_PATH = os.path.join(BASE_DIR, "data", "clean_data", "json_data", "knowledge_base.json")
    RICE_VARIETIES_PATH = os.path.join(BASE_DIR, "data", "clean_data", "json_data", "rice_varieties.json") 
    FERTILIZER_PATH = os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "fertilizer_and_water_management.txt")

    VECTOR_STORE_DIR = os.path.join(BASE_DIR, "data", "vector_store")
    VECTOR_INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "faiss_index.bin")
    VECTOR_DOCUMENTS_PATH = os.path.join(VECTOR_STORE_DIR, "documents.json")

    MODEL_VERSIONS_DIR = os.path.join(BASE_DIR, "src", "model", "versions")
    MODEL_PATH = get_latest_model_path(MODEL_VERSIONS_DIR)

    WEATHER_CACHE_PATH = os.path.join(BASE_DIR, "data", "cache", "weather_cache.json")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("Lỗi: Biến môi trường OPENAI_API_KEY chưa được thiết lập.")
    
    OPENAI_MODEL_NAME = "gpt-4o-mini" 
    OPENAI_GENERATION_CONFIG = {
        "temperature": 0.6,
        "top_p": 0.9,
        "response_format": {"type": "json_object"}
    }

    CLASS_NAMES = ["bacterial_leaf_blight", "blast", "brown_spot", "healthy"]
    WEATHER_CACHE_DURATION_HOURS = 6
    SCHEDULER_JOB_INTERVAL_MINUTES = 15

CONFIG = AppConfig()
