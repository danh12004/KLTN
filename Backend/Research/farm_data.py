import json
import random
from faker import Faker
from datetime import date, timedelta

# 1. Khởi tạo Faker để tạo tên giả (tiếng Việt)
fake = Faker('vi_VN')

# 2. Dictionary khoảng pH cho từng tỉnh 
PH_RANGE_PER_PROVINCE = {
    "An Giang": (4.5, 5.5),
    "Kien Giang": (4.2, 5.2),
    "Can Tho": (4.8, 5.8),
    "Soc Trang": (4.5, 5.5),
    "Vinh Long": (5.0, 6.0),
    "Tien Giang": (5.0, 6.0),
    "Long An": (5.2, 6.2),
    "Tra Vinh": (4.8, 5.8),
    "Bac Lieu": (4.5, 5.4),
    "Ca Mau": (4.3, 5.3),
    "Thanh Hoa": (5.5, 6.5),
    "Nam Dinh": (5.8, 6.8),
    "Nghe An": (5.7, 6.7),
    "Hai Duong": (5.9, 6.9)
}

# Lấy danh sách tỉnh tự động từ dictionary ở trên
provinces = list(PH_RANGE_PER_PROVINCE.keys())

# 3. Các thông số khác để giả lập
rice_varieties = ["OM5451", "Jasmine 85", "ST25", "Đài Thơm 8", "Nếp cái hoa vàng"]
diseases = ["đạo ôn", "đốm nâu", "cháy bìa lá", "bình thường"]
severities = ["nhẹ", "trung bình", "nặng"]

farmers_data = []
start_date = date(2009, 1, 1)
end_date = date(2021, 8, 16)
time_between_dates = end_date - start_date
days_between_dates = time_between_dates.days

print("Bắt đầu tạo dữ liệu giả lập...")

for i in range(100):
    province = random.choice(provinces)
    min_ph, max_ph = PH_RANGE_PER_PROVINCE[province]
    ph_value = round(random.uniform(min_ph, max_ph), 1)

    random_number_of_days = random.randrange(days_between_dates)
    planting_date = start_date + timedelta(days=random_number_of_days)
    
    history_year = planting_date.year - 1
    history_season = f"{random.choice(['Đông Xuân', 'Hè Thu'])} {history_year}"
    history_disease = random.choice(diseases)
    history_severity = "không có" if history_disease == "bình thường" else random.choice(severities)

    farmer = {
        "farmer_id": f"NH{i+1:03d}",
        "farmer_name": fake.name(),
        "location": { "province": province },
        "farm_properties": {
            "area_ha": round(random.uniform(0.5, 3.0), 1),
            "rice_variety": random.choice(rice_varieties),
            "planting_date": planting_date.strftime("%Y-%m-%d")
        },
        "soil_properties": {
            "ph": ph_value,
            "nitrogen_level": random.choice(["thấp", "trung bình", "cao"]),
            "potassium_level": random.choice(["thấp", "trung bình"])
        },
        "history": [{
            "season": history_season,
            "disease": history_disease,
            "severity": history_severity
        }]
    }
    farmers_data.append(farmer)

output_path = r'D:\Đồ án\KLTN\Backend\data\clean_data\farmers.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(farmers_data, f, ensure_ascii=False, indent=2)

print(f"Đã tạo thành công file '{output_path}' với {len(farmers_data)} nông hộ.")