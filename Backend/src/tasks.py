from datetime import datetime
from flask import current_app
from src.logging.logger import logger
from src.entity.models import db

def scheduled_monitoring_task(app, user_id):
    """Tác vụ giám sát được lên lịch cho MỘT người dùng cụ thể."""
    with app.app_context():
        logger.info(f"Bắt đầu tác vụ giám sát cho User ID {user_id}")
        user = current_app.user_repo.get_user_with_farm(user_id)
        
        if not user or not user.settings.notification_enabled:
            logger.warning(f"Bỏ qua User ID {user_id}, người dùng không tồn tại hoặc đã tắt thông báo.")
            job_id = f'monitoring_job_for_user_{user_id}'
            if hasattr(current_app, 'scheduler') and current_app.scheduler.get_job(job_id):
                current_app.scheduler.remove_job(job_id)
                logger.info(f"Đã xóa job '{job_id}' không còn hợp lệ.")
            return

        monitoring_agent = current_app.monitoring_agent
        farm = user.farms.first()
        if farm:
            fake_data = app.iot_service.generate_fake_data(farm.id)
            app.iot_service.save_data(farm.id, fake_data) 
            
            monitoring_agent.check_risk_for_farmer(user, iot_data=fake_data)

            user.settings.last_checked_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Hoàn tất tác vụ giám sát cho User ID {user_id}")

def scheduled_retrain_task(app):
    """Tác vụ retrain model định kỳ."""
    with app.app_context():
        from .model.retrain.retrain_pipeline import retrain_run
        logger.info("--- BẮT ĐẦU QUY TRÌNH RETRAIN ĐỊNH KỲ ---")
        retrain_run()
        logger.info("--- KẾT THÚC QUY TRÌNH RETRAIN ĐỊNH KỲ ---")
