import uuid
import json
from flask import current_app
from src.repository.base_repository import BaseRepository
from src.entity.models import db, AnalysisSession, Message

class AnalysisRepository(BaseRepository):
    def __init__(self):
        super().__init__(AnalysisSession)

    def create_session(self, farm_id: int, initial_detection: str, image_path: str = None) -> AnalysisSession:
        session_id = str(uuid.uuid4())
        new_session = AnalysisSession(
            id=session_id,
            farm_id=farm_id,
            initial_detection=initial_detection,
            image_path=image_path
        )
        return self.add(new_session)

    def update_session_plan(self, session: AnalysisSession, plan: dict):
        session.final_plan_json = json.dumps(plan, ensure_ascii=False)

    def get_session_by_id(self, session_id: str) -> AnalysisSession:
        return self.get_by_id(session_id)

    def save_chat_interaction(self, session_id: str, user_message: str, updated_plan: dict):
        try:
            session = self.get_session_by_id(session_id)
            if not session:
                raise ValueError(f"Không tìm thấy session với ID {session_id}")

            self.add(Message(sender='user', content=user_message, session_id=session_id))
            
            ai_content = updated_plan.get("treatment_plan", {}).get("main_message", "Kế hoạch đã được cập nhật.")
            self.add(Message(sender='ai', content=ai_content, session_id=session_id))

            self.update_session_plan(session, updated_plan)
            
            self.commit()
            return {"success": True}
        except Exception as e:
            self.rollback()
            current_app.logger.error(f"Lỗi khi lưu chat interaction: {e}")
            return {"error": "Lỗi hệ thống khi lưu cuộc hội thoại."}

    def get_latest_session_for_farm(self, farm_id: int) -> AnalysisSession:
        return AnalysisSession.query.filter_by(farm_id=farm_id)\
            .order_by(AnalysisSession.created_at.desc())\
            .first()

    def get_all_sessions_for_farm(self, farm_id: int):
        return AnalysisSession.query.filter_by(farm_id=farm_id)\
            .order_by(AnalysisSession.created_at.desc())\
            .all()
    
    def get_or_create_qa_session(self, farm_id: int):
        session = AnalysisSession.query.filter_by(
            farm_id=farm_id, 
            initial_detection='Hỏi đáp chung'
        ).first()

        if session:
            return session

        new_session = self.create_session(farm_id, 'Hỏi đáp chung')
        self.commit()
        return new_session

    def save_qa_message(self, session_id: str, question: str, answer: str):
        try:
            self.add(Message(sender='user', content=question, session_id=session_id))
            self.add(Message(sender='ai', content=answer, session_id=session_id))
            self.commit()
        except Exception as e:
            self.rollback()
            current_app.logger.error(f"Lỗi khi lưu tin nhắn Q&A: {e}")

    def update_session_status(self, session_id: str, status: str):
        try:
            session = self.get_session_by_id(session_id)
            if session:
                session.status = status
                self.commit()
            return session
        except Exception as e:
            self.rollback()
            return None