import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_apscheduler import APScheduler
from datetime import datetime

from .utils.config import CONFIG
from .entity.models import db, bcrypt, User, UserSettings
from .repository.user_repository import UserRepository
from .repository.analysis_repository import AnalysisRepository
from .services.weather_service import WeatherService
from .services.vector_store_service import VectorStoreService
from .services.iot_service import IoTService

from .agents.image_recognition_agent import ImageRecognitionAgent
from .agents.treatment_agent import TreatmentAgent
from .agents.nutrient_agent import NutrientAgent
from .agents.water_agent import WaterAgent
from .agents.action_agent import ActionAgent
from .agents.qa_agent import QAAgent
from .agents.monitoring_agent import EnvironmentalMonitoringAgent

from .tasks import scheduled_monitoring_task, scheduled_retrain_task

scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object(CONFIG)
    
    CORS(app, supports_credentials=True)
    db.init_app(app)
    bcrypt.init_app(app)
    jwt = JWTManager(app)

    from .api.auth import auth_bp
    from .api.admin_routes import admin_bp
    from .api.user_routes import user_bp
    from .api.treatment_routes import treatment_bp
    from .api.farm_management_routes import farm_management_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth') 
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(treatment_bp, url_prefix='/api/treatment')
    app.register_blueprint(farm_management_bp, url_prefix='/api/farm')
    
    with app.app_context():
        db.create_all()

        app.user_repo = UserRepository()
        app.analysis_repo = AnalysisRepository()
        app.weather_service = WeatherService()
        app.iot_service = IoTService()
        app.vector_store = VectorStoreService(CONFIG)
        app.image_agent = ImageRecognitionAgent(model_path=CONFIG.MODEL_PATH, class_names=CONFIG.CLASS_NAMES)
        app.treatment_agent = TreatmentAgent(weather_service=app.weather_service, user_repo=app.user_repo, analysis_repo=app.analysis_repo, vector_store=app.vector_store)
        app.nutrient_agent = NutrientAgent(weather_service=app.weather_service, user_repo=app.user_repo, analysis_repo=app.analysis_repo, vector_store=app.vector_store)
        app.water_agent = WaterAgent(weather_service=app.weather_service, user_repo=app.user_repo, analysis_repo=app.analysis_repo, vector_store=app.vector_store)
        app.action_agent = ActionAgent()
        app.monitoring_agent = EnvironmentalMonitoringAgent(treatment_agent=app.treatment_agent, image_agent=app.image_agent, user_repo=app.user_repo, storage_folder=CONFIG.STORAGE_FOLDER)
        app.qa_agent = QAAgent(
            vector_store=app.vector_store,
            nutrient_agent=app.nutrient_agent,
            treatment_agent=app.treatment_agent,
            water_agent=app.water_agent,
            environmental_agent=app.monitoring_agent
        )
        app.pending_plans = {}
        app.scheduler = scheduler

        print("\n--- BẮT ĐẦU TẢI/XÂY DỰNG CÁC KHO VECTOR TRI THỨC ---")
        
        if hasattr(CONFIG, 'KNOWLEDGE_SOURCES') and isinstance(CONFIG.KNOWLEDGE_SOURCES, dict):
            knowledge_store_names = list(CONFIG.KNOWLEDGE_SOURCES.keys())
            for store_name in knowledge_store_names:
                print(f"Đang kiểm tra và khởi tạo kho tri thức: '{store_name}'...")
                app.vector_store.get_store(store_name)
            print("--- TẤT CẢ CÁC KHO VECTOR ĐÃ SẴN SÀNG ---\n")
        else:
            print("!!! Cảnh báo: Không tìm thấy định nghĩa KNOWLEDGE_SOURCES trong config. Bỏ qua việc pre-load vector stores.")

        print("--- HỆ THỐNG AI ĐÃ SẴN SÀNG ---")

        if not app.scheduler.running:
            app.scheduler.init_app(app)
            app.scheduler.start()
            print("Scheduler đã được khởi tạo và bắt đầu.")

        users_to_schedule = User.query.join(UserSettings).filter(UserSettings.notification_enabled == True).all()
        print(f"--- BẮT ĐẦU LÊN LỊCH GIÁM SÁT CHO {len(users_to_schedule)} NGƯỜI DÙNG ---")
        for user in users_to_schedule:
            job_id = f'monitoring_job_for_user_{user.id}'
            if not scheduler.get_job(job_id):
                scheduler.add_job(
                    id=job_id,
                    func=scheduled_monitoring_task,
                    args=[app, user.id],
                    trigger='interval',
                    hours=user.settings.notification_interval_hours
                )
                print(f"Đã lên lịch job '{job_id}' cho user {user.id}, mỗi {user.settings.notification_interval_hours} giờ.")
        print("--- KẾT THÚC LÊN LỊCH BAN ĐẦU ---")
        
        if not scheduler.get_job('Scheduled Retrain'):
            scheduler.add_job(id='Scheduled Retrain', func=scheduled_retrain_task, args=[app], trigger='interval', weeks=26)
            print("Job 'Scheduled Retrain' đã được thêm, chạy mỗi 6 tháng.")

    return app