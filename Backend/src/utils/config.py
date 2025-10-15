import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_latest_model_path(models_dir, prefix="efficientnet_model_v", ext=".keras"):
    """Tìm và trả về đường dẫn của phiên bản model mới nhất trong một thư mục."""
    if not os.path.isdir(models_dir):
        return None
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

    STORAGE_FOLDER = os.path.join(BASE_DIR, "data", "storage")
    IOT_FOLDER = os.path.join(BASE_DIR, "data", "clean_data")
    WEATHER_CACHE_PATH = os.path.join(BASE_DIR, "data", "cache", "weather_cache.json")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 

    VECTOR_STORE_DIR = os.path.join(BASE_DIR, "data", "vector_store")
    
    KNOWLEDGE_SOURCES = {
        "bacterial_leaf_blight": [
            {
                "id": "bacterial_leaf_blight_control",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "bacterial_leaf_blight.txt"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Phòng trừ Cháy bìa lá"}
            },
            {
                "id": "bacterial_leaf_blight_drug", 
                "type": "json",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "json_data", "bacterial_leaf_blight.json"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Thông tin thuốc"}
            }
        ],
        "blast": [
            {
                "id": "blast_control",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "blast.txt"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Phòng trừ Đạo ôn"}
            },
            {
                "id": "blast_drug", 
                "type": "json",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "json_data", "blast.json"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Thông tin thuốc"}
            }
        ],
        "brown_spot": [
            {
                "id": "brown_spot_control",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "brown_spot.txt"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Phòng trừ Đốm nâu"}
            },
            {
                "id": "brown_spot_drug", 
                "type": "json",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "json_data", "brown_spot.json"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Thông tin thuốc"}
            }
        ],

        "fertilizer_management": [
            {
                "id": "fertilizer_management",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "fertilizer_management.txt"),
                "metadata": {"topic": "Quản lý phân bón"}
            }
        ],
        "water_management": [
            {
                "id": "water_management",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "water_management.txt"),
                "metadata": {"topic": "Quản lý nước"}
            }
        ],

        "general_qa": [
            {
                "id": "bacterial_leaf_blight_drug_qa",
                "type": "json",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "json_data", "bacterial_leaf_blight.json"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Thuốc trị Cháy bìa lá"}
            },
            {
                "id": "blast_drug_qa",
                "type": "json",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "json_data", "blast.json"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Thuốc trị Đạo ôn"}
            },
            {
                "id": "brown_spot_drug_qa",
                "type": "json",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "json_data", "brown_spot.json"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Thuốc trị Đốm nâu"}
            },
            {
                "id": "bacterial_leaf_blight_control_qa",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "bacterial_leaf_blight.txt"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Phòng trừ Cháy bìa lá"}
            },
            {
                "id": "blast_control_qa",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "blast.txt"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Phòng trừ Đạo ôn"}
            },
            {
                "id": "brown_spot_control_qa",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "brown_spot.txt"),
                "metadata": {"topic": "Bệnh hại lúa", "sub_topic": "Phòng trừ Đốm nâu"}
            },
            {
                "id": "fertilizer_management_qa",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "fertilizer_management.txt"),
                "metadata": {"topic": "Quản lý phân bón"}
            },
            {
                "id": "water_management_qa",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "water_management.txt"),
                "metadata": {"topic": "Quản lý nước"}
            },
            {
                "id": "rice_varieties_qa",
                "type": "json",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "json_data", "rice_varieties.json"),
                "metadata": {"topic": "Giống lúa", "sub_topic_key": "rice_variety"}
            },
            {
                "id": "doc_qa",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "doc.txt"),
                "metadata": {"topic": "Thông tin chung"}
            },
            {
                "id": "weeds_qa",
                "type": "txt",
                "path": os.path.join(BASE_DIR, "data", "clean_data", "txt_data", "weed_knowledge.txt"),
                "metadata": {"topic": "Quản lý cỏ dại"}
            }
        ]
    }

    MODEL_VERSIONS_DIR = os.path.join(BASE_DIR, "src", "model", "versions")
    MODEL_PATH = get_latest_model_path(MODEL_VERSIONS_DIR)
    CLASS_NAMES = ["bacterial_leaf_blight", "blast", "brown_spot", "healthy"]

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("Lỗi: Biến môi trường OPENAI_API_KEY chưa được thiết lập.")
    
    OPENAI_MODEL_NAME = "gpt-4o-mini"  
    OPENAI_GENERATION_CONFIG = {
        "temperature": 0.4,
        "top_p": 0.9,
        "max_tokens": 2048,  
        "seed": 12345         
    }

    WEATHER_CACHE_DURATION_HOURS = 6

CONFIG = AppConfig()

