from app import create_app
from src.entity.models import db
from src.logging.logger import logger

app = create_app()

with app.app_context():
    logger.info("Đang tạo các bảng trong database...")
    try:
        db.create_all()
        logger.info("Các bảng đã được tạo thành công!")
    except Exception as e:
        logger.error(f"Đã xảy ra lỗi khi tạo bảng: {e}")
