from app import create_app
from src.entity.models import db
app = create_app()

with app.app_context():
    print("Đang tạo các bảng trong database...")
    db.create_all()
    print("Các bảng đã được tạo thành công!")