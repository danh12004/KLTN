from src.repository.base_repository import BaseRepository
from src.entity.models import db, AnalysisSession

class AdminAnalysisRepository(BaseRepository):
    def __init__(self):
        super().__init__(AnalysisSession)

    def get_all_sessions(self):
        return AnalysisSession.query.all()
    
    def delete_session(self, session_id: str):
        session = self.get_by_id(session_id)
        if session:
            self.delete(session)
            self.commit()
            return True
        return False
