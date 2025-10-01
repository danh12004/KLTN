import random
import uuid
import json
from faker import Faker
from datetime import date, timedelta, datetime

from app import create_app
from src.entity.models import db, User, Farm, AnalysisSession, Message, UserSettings

app = create_app()
fake = Faker('vi_VN') 

PH_RANGE_PER_PROVINCE = {
    "An Giang": (4, 5.5), "Đồng Tháp": (4.5, 5.5), "Cần Thơ": (5.0, 6.5), 
    "Hà Nội": (5.5, 6.5), "Ninh Bình": (4.5, 6.5)
}
provinces = list(PH_RANGE_PER_PROVINCE.keys())
DISEASES = ["Đạo ôn", "Đốm nâu", "Cháy bìa lá", "Khỏe mạnh"]
INTERVAL_OPTIONS = [1, 4, 8, 12, 24]
SESSION_STATUSES = ['đã hoàn thành', 'đang chờ', 'đang tiến hành']

AI_MESSAGES = [
    "Dựa trên phân tích, lúa của bác có dấu hiệu bệnh đốm nâu. Tôi đề xuất phun thuốc Anvil 5SC.",
    "Lúa của bác hoàn toàn khỏe mạnh. Bác hãy tiếp tục duy trì chế độ chăm sóc hiện tại nhé.",
    "Phát hiện bệnh cháy bìa lá ở giai đoạn đầu. Bác cần phun thuốc Sasa 25WP ngay vào sáng mai.",
    "Đã ghi nhận yêu cầu của bác. Kế hoạch sẽ được cập nhật.",
]
USER_MESSAGES = [
    "Cảm ơn trợ lý.",
    "Tôi có thể phun vào buổi chiều được không?",
    "Liều lượng cụ thể là bao nhiêu?",
    "Được rồi, tôi đã hiểu.",
]

RICE_VARIETIES = ["OM7347", "ST25", "ST24", "ST 21-3", "Dai Thom 8"]

def create_fake_plan(disease_name, farm_area_ha):
    if disease_name == "Khỏe mạnh":
        return None
    
    drug_map = {
        "Đạo ôn": {"name": "Beam 75WP", "active": "Tricyclazole"},
        "Đốm nâu": {"name": "Anvil 5SC", "active": "Hexaconazole"},
        "Cháy bìa lá": {"name": "Sasa 25WP", "active": "Kasugamycin"}
    }
    drug = drug_map.get(disease_name, {"name": "Thuốc chung", "active": "Hoạt chất chung"})
    
    total_dosage = round(farm_area_ha * random.uniform(0.8, 1.2), 2)

    return json.dumps({
        "analysis": {
            "risk_assessment": f"Bệnh {disease_name} có nguy cơ lây lan nhanh do thời tiết ẩm.",
            "weather_summary": "Dự báo trời có mây, ít mưa, thuận lợi cho việc phun thuốc."
        },
        "treatment_plan": {
            "main_message": f"Đề xuất phun thuốc {drug['name']} để xử lý bệnh {disease_name}.",
            "optimal_spray_day": {
                "date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                "session": "Sáng",
                "reason": "Thời tiết khô ráo, ít gió, hiệu quả thuốc cao nhất."
            },
            "drug_info": {
                "sản_phẩm_tham_khảo": drug['name'],
                "hoạt_chất": drug['active'],
                "liều_lượng": f"Tổng cộng {total_dosage} kg cho {farm_area_ha} ha.",
                "cách_dùng": "Pha theo hướng dẫn trên bao bì, phun ướt đều tán lá."
            }
        },
        "prognosis": "Nếu tuân thủ kế hoạch, bệnh sẽ được kiểm soát trong 5-7 ngày."
    }, ensure_ascii=False)


with app.app_context():
    print("Bắt đầu quá trình nạp dữ liệu (seeding)...")
    
    print("-> Bước 1: Xóa toàn bộ dữ liệu cũ...")
    Message.query.delete()
    AnalysisSession.query.delete()
    Farm.query.delete()
    UserSettings.query.delete() 
    User.query.delete()
    db.session.commit()
    
    print("-> Bước 2: Tạo tài khoản Admin...")
    admin_user = User(
        username='admin',
        password='123456',
        full_name='Quản Trị Viên',
        role='admin'
    )
    db.session.add(admin_user)
    
    admin_settings = UserSettings(user=admin_user)
    db.session.add(admin_settings)

    print(f"-> Bước 3: Tạo dữ liệu cho 6 nông hộ...")
    for i in range(6):
        farmer_user = User(
            username=f'nongdan{i+1}',
            password=f'password{i+1}',
            full_name=fake.name(),
            role='farmer'
        )
        db.session.add(farmer_user)

        farmer_settings = UserSettings(
            notification_enabled=random.choice([True, False]),
            notification_interval_hours=random.choice(INTERVAL_OPTIONS),
            user=farmer_user 
        )
        db.session.add(farmer_settings)

        province = random.choice(provinces)
        min_ph, max_ph = PH_RANGE_PER_PROVINCE[province]
        
        farm = Farm(
            name=f"Ruộng nhà bác {farmer_user.full_name.split()[-1]}",
            province=province,
            area_ha=round(random.uniform(0.5, 2.0), 1),
            planting_date=date.today() - timedelta(days=random.randint(20, 100)),
            soil_ph=round(random.uniform(min_ph, max_ph), 1),
            rice_variety=random.choice(RICE_VARIETIES), 
            owner=farmer_user
        )
        db.session.add(farm)

        for _ in range(random.randint(1, 4)):
            session_time = datetime.now() - timedelta(days=random.randint(1, 15))
            detected_disease = random.choice(DISEASES)
            
            session = AnalysisSession(
                id=str(uuid.uuid4()),
                created_at=session_time,
                image_path=f"/uploads/fake_images/rice_leaf_{random.randint(1, 20)}.jpg",
                initial_detection=detected_disease,
                final_plan_json=create_fake_plan(detected_disease, farm.area_ha),
                status=random.choice(SESSION_STATUSES), 
                farm=farm
            )
            db.session.add(session)
            
            if session.status != 'pending':
                ai_first_message = Message(sender='ai', content=random.choice(AI_MESSAGES), timestamp=session_time, session=session)
                user_reply_message = Message(sender='user', content=random.choice(USER_MESSAGES), timestamp=session_time + timedelta(hours=1), session=session)
                db.session.add(ai_first_message)
                db.session.add(user_reply_message)

    print("-> Bước 4: Lưu tất cả dữ liệu vào database...")
    db.session.commit()

    print("-" * 30)
    print(" HOÀN TẤT ".center(30, "="))
    print(f"Tổng số Users: {User.query.count()} ({User.query.filter_by(role='admin').count()} admin, {User.query.filter_by(role='farmer').count()} farmer)")
    print(f"Tổng số UserSettings: {UserSettings.query.count()}")
    print(f"Tổng số Farms: {Farm.query.count()}")
    print(f"Tổng số Sessions: {AnalysisSession.query.count()}")
    print(f"Tổng số Messages: {Message.query.count()}")
    print("-" * 30)