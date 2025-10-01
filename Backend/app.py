import os
from flask import Flask, current_app
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta

from src.utils.config import CONFIG
from src.entity.models import db, bcrypt, User, UserSettings
from src.repository.user_repository import UserRepository
from src.repository.analysis_repository import AnalysisRepository
from src.services.weather_service import WeatherService
from src.services.vector_store_service import VectorStoreService
from src.agents.image_recognition_agent import ImageRecognitionAgent
from src.agents.decision_agent import DecisionAgent
from src.agents.action_agent import ActionAgent
from src.agents.qa_agent import QAAgent
from src.agents.monitoring_agent import EnvironmentalMonitoringAgent
from src.services.iot_service import IoTService
from src.model.retrain.retrain_pipeline import retrain_run

scheduler = APScheduler()

def scheduled_monitoring_task(app):
    with app.app_context():
        print(f"\n[{datetime.now()}] --- BẮT ĐẦU QUÉT TÁC VỤ GIÁM SÁT ---")
        monitoring_agent = current_app.monitoring_agent
        
        users_to_check = User.query.join(UserSettings).filter(UserSettings.notification_enabled == True).all()

        for user in users_to_check:
            settings = user.settings
            now = datetime.utcnow()
            
            should_check = False
            if settings.last_checked_at is None:
                should_check = True
            else:
                time_since_last_check = now - settings.last_checked_at
                required_interval = timedelta(hours=settings.notification_interval_hours)
                if time_since_last_check >= required_interval:
                    should_check = True

            if should_check:
                farm = user.farms.first()
                if farm:
                    fake_data = app.iot_service.generate_fake_data(farm.id)
                    app.iot_service.save_to_json(farm.id, fake_data)
                    monitoring_agent.check_risk_for_farmer(user, iot_data=fake_data)

                settings.last_checked_at = now
                db.session.commit()
            else:
                print(f"Bỏ qua User ID {user.id}, chưa đến thời gian quét.")
        print(f"[{datetime.now()}] --- KẾT THÚC QUÉT TÁC VỤ ---")

def scheduled_retrain_task(app):
    with app.app_context():
        print(f"\n[{datetime.now()}] --- BẮT ĐẦU QUY TRÌNH RETRAIN ---")
        retrain_run()
        print(f"[{datetime.now()}] --- KẾT THÚC QUY TRÌNH RETRAIN ---")

def create_app():
    app = Flask(__name__)
    
    app.config.from_object(CONFIG)
    
    CORS(app, supports_credentials=True, 
         expose_headers=['Authorization'],
         allow_headers=['Content-Type', 'Authorization'])
    db.init_app(app)
    bcrypt.init_app(app)
    jwt = JWTManager(app)

    from src.api.auth import auth_bp
    from src.api.routes import api_bp
    from src.api.admin_routes import admin_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    with app.app_context():
        db.create_all()

        print("--- KHỞI TẠO HỆ THỐNG TRỢ LÝ AI ---")
        
        app.user_repo = UserRepository()
        app.analysis_repo = AnalysisRepository()
        app.weather_service = WeatherService()
        app.iot_service = IoTService()
        
        vector_store_config = {
            "knowledge_base_path": CONFIG.KNOWLEDGE_BASE_PATH,
            "rice_varieties_path": CONFIG.RICE_VARIETIES_PATH,
            "fertilizer_path": CONFIG.FERTILIZER_PATH,
            "vector_index_path": CONFIG.VECTOR_INDEX_PATH,
            "vector_documents_path": CONFIG.VECTOR_DOCUMENTS_PATH
        }
        app.vector_store = VectorStoreService(vector_store_config)

        app.image_agent = ImageRecognitionAgent(
            model_path=CONFIG.MODEL_PATH, 
            class_names=CONFIG.CLASS_NAMES
        )
        app.decision_agent = DecisionAgent(
            weather_service=app.weather_service,
            user_repo=app.user_repo,
            analysis_repo=app.analysis_repo,
            vector_store=app.vector_store
        )
        app.action_agent = ActionAgent()
        app.qa_agent = QAAgent(vector_store=app.vector_store)
        
        app.monitoring_agent = EnvironmentalMonitoringAgent(
            decision_agent=app.decision_agent,
            image_agent=app.image_agent,
            storage_folder=CONFIG.STORAGE_FOLDER
        )
        
        app.pending_plans = {}

        print("--- HỆ THỐNG AI ĐÃ SẴN SÀNG ---")

        if not scheduler.running:
            scheduler.init_app(app)
            scheduler.start()
            print("Scheduler đã được khởi tạo và bắt đầu.")

        if not scheduler.get_job('Scheduled Monitoring'):
            scheduler.add_job(
                id='Scheduled Monitoring', 
                func=scheduled_monitoring_task, 
                args=[app],
                trigger='interval', 
                minutes=CONFIG.SCHEDULER_JOB_INTERVAL_MINUTES
            )
            print(f"Job 'Scheduled Monitoring' đã được thêm vào scheduler, chạy mỗi {CONFIG.SCHEDULER_JOB_INTERVAL_MINUTES} phút.")

        if not scheduler.get_job('Scheduled Retrain'):
            scheduler.add_job(
                id='Scheduled Retrain',
                func=scheduled_retrain_task,
                args=[app],
                trigger='interval',
                weeks=26  
            )
            print("Job 'Scheduled Retrain' đã được thêm vào scheduler, chạy mỗi 6 tháng.")

    return app

if __name__ == '__main__':
    app = create_app()
    
    if not os.path.exists(CONFIG.STORAGE_FOLDER):
        os.makedirs(CONFIG.STORAGE_FOLDER)
        print(f"Đã tạo thư mục lưu trữ tại: {CONFIG.STORAGE_FOLDER}")

    app.run(debug=True, port=5000, use_reloader=False)