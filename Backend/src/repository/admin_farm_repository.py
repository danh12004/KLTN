from src.repository.base_repository import BaseRepository
from src.entity.models import db, Farm

class AdminFarmRepository(BaseRepository):
    def __init__(self):
        super().__init__(Farm)

    def get_all_farms(self):
        return Farm.query.all()
    
    def delete_farm(self, farm_id: int):
        farm = self.get_by_id(farm_id)
        if farm:
            self.delete(farm)
            self.commit()
            return True
        return False
