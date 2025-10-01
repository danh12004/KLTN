from src.repository.base_repository import BaseRepository
from src.entity.models import db, User, bcrypt

class AdminUserRepository(BaseRepository):
    def __init__(self):
        super().__init__(User)

    def get_all_users(self):
        return User.query.all()
    
    def create_user(self, username, password, full_name=None, role="farmer"):
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            username=username,
            password_hash=hashed_password, 
            full_name=full_name,
            role=role
        )
        self.add(new_user) 
        return new_user
    
    def delete_user(self, user_id: int):
        user = self.get_by_id(user_id)
        if user:
            self.delete(user)
            self.commit()
            return True
        return False
