from datetime import datetime
from flask import current_app
from src.repository.base_repository import BaseRepository
from src.entity.models import db, User, Farm, UserSettings

class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(User)

    def get_user_with_farm(self, user_id: int):
        return self.get_by_id(user_id) 

    def get_settings_by_user_id(self, user_id: int):
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            settings = self.add(UserSettings(user_id=user_id))
            self.commit()
        return settings

    def update_user_settings(self, user_id: int, settings_data: dict, farm_data: dict):
        try:
            user = self.get_by_id(user_id)
            if not user:
                raise ValueError("Không tìm thấy người dùng.")

            if settings_data:
                settings = user.settings or UserSettings(user_id=user_id)
                settings.notification_enabled = settings_data.get('enabled', settings.notification_enabled)
                settings.notification_interval_hours = settings_data.get('interval', settings.notification_interval_hours)
                self.add(settings)

            if farm_data:
                farm = user.farms.first()
                if not farm:
                     raise ValueError("Không tìm thấy nông trại.")
                
                farm.name = farm_data.get('name', farm.name)
                farm.province = farm_data.get('province', farm.province)
                
                if 'area_ha' in farm_data:
                    farm.area_ha = float(farm_data['area_ha'])
                if 'planting_date' in farm_data and farm_data['planting_date']:
                    farm.planting_date = datetime.strptime(farm_data['planting_date'], '%Y-%m-%d').date()

            self.commit()
            return {"success": True}
        except Exception as e:
            self.rollback()
            current_app.logger.error(f"Lỗi khi cập nhật cài đặt: {e}")
            return {"error": "Lỗi server khi lưu cài đặt."}