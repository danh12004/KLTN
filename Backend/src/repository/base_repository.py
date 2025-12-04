from src.entity.models import db

class BaseRepository:
    def __init__(self, model):
        self.model = model

    def get_by_id(self, item_id):
        return self.model.query.get(item_id)
    
    def add(self, item):
        db.session.add(item)
        return item
    
    def commit(self):
        db.session.commit()

    def rollback(self):
        db.session.rollback()

    def delete(self, item):
        db.session.delete(item)