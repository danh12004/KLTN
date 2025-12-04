import random
import uuid
import json
from faker import Faker
from datetime import date, timedelta, datetime

# Thay đổi import app, giả định file này nằm trong thư mục gốc
from app import create_app 
from src.entity.models import db, User, Farm, UserSettings
from src.logging.logger import logger

# Khởi tạo ứng dụng
app = create_app()
fake = Faker('vi_VN') 

# Dữ liệu giả lập
PH_RANGE_PER_PROVINCE = {
    "An Giang": (4.0, 5.5), "Đồng Tháp": (4.5, 5.5), "Cần Thơ": (5.0, 6.5), 
    "Hà Nội": (5.5, 6.5), "Ninh Bình": (4.5, 6.5), "Sóc Trăng": (4.0, 5.0),
    "Kiên Giang": (4.5, 6.0)
}
provinces = list(PH_RANGE_PER_PROVINCE.keys())
INTERVAL_OPTIONS = [1, 4, 8, 12, 24]
RICE_VARIETIES = ["OM7347", "ST25", "ST24", "ST 21-3", "Dai Thom 8"]
SOIL_TYPES = ["đất phù sa", "đất phèn", "đất mặn", "đất sét", "đất thịt trung bình"]


with app.app_context():
    logger.info("Bắt đầu quá trình nạp dữ liệu (seeding) tinh gọn: Users & Farms...")
    
    logger.info("-> Bước 1: Xóa toàn bộ dữ liệu cũ (Users, Settings, Farms)...")
    # Chúng ta chỉ xóa các bảng liên quan: Message và AnalysisSession đã bị loại bỏ
    # nhưng nếu vẫn cần đảm bảo sạch sẽ, nên giữ lại lệnh xóa này.
    from src.entity.models import AnalysisSession, Message # Giả định import này là cần thiết
    Message.query.delete()
    AnalysisSession.query.delete()
    Farm.query.delete()
    UserSettings.query.delete() 
    User.query.delete()
    db.session.commit()
    
    logger.info("-> Bước 2: Tạo tài khoản Admin...")
    admin_user = User(
        username='admin',
        password='123456',
        full_name='Quản Trị Viên',
        role='admin'
    )
    db.session.add(admin_user)
    # Thêm cài đặt cho Admin
    db.session.add(UserSettings(user=admin_user)) 

    logger.info("-> Bước 3: Tạo dữ liệu cho 6 nông hộ và Farm...")
    for i in range(6):
        # 3.1. Tạo User
        farmer_user = User(
            username=f'nongdan{i+1}',
            password=f'password{i+1}',
            full_name=fake.name(),
            role='farmer'
        )
        db.session.add(farmer_user)

        # 3.2. Tạo User Settings
        db.session.add(UserSettings(
            notification_enabled=random.choice([True, False]),
            notification_interval_hours=random.choice(INTERVAL_OPTIONS),
            user=farmer_user 
        ))

        # 3.3. Tạo Farm
        province = random.choice(provinces)
        min_ph, max_ph = PH_RANGE_PER_PROVINCE[province]
        
        farm = Farm(
            name=f"Ruộng nhà bác {farmer_user.full_name.split()[-1]}",
            province=province,
            area_ha=round(random.uniform(0.5, 2.0), 1),
            planting_date=date.today() - timedelta(days=random.randint(20, 70)),
            soil_ph=round(random.uniform(min_ph, max_ph), 1),
            soil_type=random.choice(SOIL_TYPES), 
            rice_variety=random.choice(RICE_VARIETIES), 
            owner=farmer_user
        )
        db.session.add(farm)

        # *** LOẠI BỎ logic tạo AnalysisSession và Message giả ***

    logger.info("-> Bước 4: Lưu tất cả dữ liệu vào database...")
    db.session.commit()

    logger.info("-" * 30)
    logger.info(" HOÀN TẤT ".center(30, "="))
    logger.info(f"Tổng số Users: {User.query.count()} ({User.query.filter_by(role='admin').count()} admin, {User.query.filter_by(role='farmer').count()} farmer)")
    logger.info(f"Tổng số UserSettings: {UserSettings.query.count()}")
    logger.info(f"Tổng số Farms: {Farm.query.count()}")
    
    # Do đã xóa, nên các giá trị này sẽ là 0 (nếu không có dữ liệu nào khác được tạo trong app_context)
    logger.info(f"Tổng số Sessions: {AnalysisSession.query.count()}")
    logger.info(f"Tổng số Messages: {Message.query.count()}")
    
    logger.info("-" * 30)