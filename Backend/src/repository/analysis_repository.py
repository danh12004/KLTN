import uuid
import json
from flask import current_app
from sqlalchemy.sql import case
from src.repository.base_repository import BaseRepository
from src.entity.models import db, AnalysisSession, Message
from datetime import datetime, timezone

class AnalysisRepository(BaseRepository):
    """
    Repository để quản lý tất cả các tương tác liên quan đến 
    phiên phân tích và chẩn đoán.
    """
    def __init__(self):
        super().__init__(AnalysisSession)

    def create_session(self, farm_id: int, initial_detection: str, plan_type: str = 'treatment', image_path: str = None, status: str = "Chờ xác nhận") -> AnalysisSession:
        """
        Tạo một phiên phân tích mới.
        
        Args:
            farm_id: ID của nông trại.
            initial_detection: Chẩn đoán ban đầu (ví dụ: "Đạo ôn", "Kế hoạch bón phân").
            plan_type: Loại kế hoạch ('treatment', 'fertilizer', 'water'). Mặc định là 'treatment'.
            image_path: Đường dẫn đến ảnh (nếu có).
            status: Trạng thái ban đầu của phiên.
            
        Returns:
            Đối tượng AnalysisSession vừa được tạo.
        """
        session_id = str(uuid.uuid4())
        new_session = AnalysisSession(
            id=session_id,
            farm_id=farm_id,
            initial_detection=initial_detection,
            image_path=image_path,
            plan_type=plan_type,  
            status=status        
        )
        return self.add(new_session)

    def update_session_plan(self, session: AnalysisSession, plan: dict):
        """Cập nhật kế hoạch (dạng JSON) cho một session."""
        session.final_plan_json = json.dumps(plan, ensure_ascii=False)
        
    def update_session_executed_payload(self, session_id: str, payload_json: str):
        try:
            session = self.get_session_by_id(session_id)
            if session:
                session.executed_payload_json = payload_json
            return session
        except Exception as e:
            current_app.logger.error(f"Lỗi khi cập nhật executed_payload_json cho session {session_id}: {e}")
            self.rollback()
            return None

    def get_session_by_id(self, session_id: str) -> AnalysisSession:
        """Lấy một session bằng ID của nó."""
        return self.get_by_id(session_id)

    def find_session_by_id(self, session_id: str) -> AnalysisSession:
        """
        Đây là một phương thức alias để tương thích với code đã gọi nó.
        Nó sẽ gọi đến phương thức get_session_by_id.
        """
        return self.get_session_by_id(session_id)
    
    def find_latest_executed_session(self, plan_type: str = None) -> AnalysisSession:
        """
        Tìm phiên làm việc gần nhất đã có executed_payload_json được điền.
        Có thể tùy chọn lọc theo plan_type.
        """
        query = AnalysisSession.query
        
        query = query.filter(AnalysisSession.executed_payload_json.isnot(None))
        
        if plan_type:
            query = query.filter_by(plan_type=plan_type)
        
        return query.order_by(AnalysisSession.created_at.desc()).first()

    def save_chat_interaction(self, session_id: str, user_message: str, updated_plan: dict):
        """Lưu lại một lượt tương tác chat (user và ai) vào CSDL."""
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

    def get_latest_session_for_farm_by_type(self, farm_id: int, plan_type: str) -> AnalysisSession:
        """Lấy session gần nhất của một nông trại theo loại kế hoạch."""
        return AnalysisSession.query.filter_by(farm_id=farm_id, plan_type=plan_type)\
            .order_by(AnalysisSession.created_at.desc())\
            .first()

    def get_all_sessions_for_farm(self, farm_id: int):
        """Lấy tất cả session của một nông trại, sắp xếp từ mới nhất đến cũ nhất."""
        return AnalysisSession.query.filter_by(farm_id=farm_id)\
            .order_by(AnalysisSession.created_at.desc())\
            .all()
    
    def get_or_create_qa_session(self, farm_id: int):
        """Lấy hoặc tạo session dùng cho mục đích Hỏi & Đáp chung."""
        session = AnalysisSession.query.filter_by(
            farm_id=farm_id, 
            initial_detection='Hỏi đáp chung',
            plan_type='qa' 
        ).first()

        if session:
            return session

        new_session = self.create_session(
            farm_id=farm_id, 
            initial_detection='Hỏi đáp chung',
            plan_type='qa'
        )
        self.commit()
        return new_session

    def save_qa_message(self, session_id: str, question: str, answer: str):
        """Lưu tin nhắn cho phiên Hỏi & Đáp."""
        try:
            self.add(Message(sender='user', content=question, session_id=session_id))
            self.add(Message(sender='ai', content=answer, session_id=session_id))
            self.commit()
        except Exception as e:
            self.rollback()
            current_app.logger.error(f"Lỗi khi lưu tin nhắn Q&A: {e}")

    def update_session_status(self, session_id: str, status: str):
        """Cập nhật trạng thái (status) của một session."""
        try:
            session = self.get_session_by_id(session_id)
            if session:
                session.status = status
            return session
        except Exception as e:
            current_app.logger.error(f"Lỗi khi cập nhật trạng thái session {session_id}: {e}")
            self.rollback()
            return None
        
    def get_sessions_for_farm_by_type_prioritized(self, farm_id: int, plan_type: str, limit: int = 3):
        status_order = case(
            (AnalysisSession.status == 'Đang xử lý', 1),
            (AnalysisSession.status == 'Đã xử lý', 2),
            (AnalysisSession.status == 'Chờ xử lý', 3),
            else_=4
        )

        return AnalysisSession.query.filter_by(farm_id=farm_id, plan_type=plan_type)\
            .order_by(status_order, AnalysisSession.created_at.desc())\
            .limit(limit).all()
            
    def find_sessions_pending_follow_up(self) -> list[AnalysisSession]:
        """
        Tìm tất cả các phiên làm việc đã đến hạn theo dõi lại.
        Điều kiện: follow_up_time đã đến hoặc đã qua, và follow_up_status là 'Chờ theo dõi'.
        """
        now_utc = datetime.now(timezone.utc)
        
        return AnalysisSession.query.filter(
            AnalysisSession.follow_up_status == 'Chờ theo dõi',
            AnalysisSession.follow_up_time.isnot(None),
            AnalysisSession.follow_up_time <= now_utc
        ).all()
    
    @staticmethod
    def _parse_plan_summary(session):
        """Trích xuất loại kế hoạch, chẩn đoán, và đánh giá rủi ro/khuyến nghị từ plan JSON."""
        if not session.final_plan_json:
            return "Không rõ", session.initial_detection, "N/A"

        try:
            plan_data = json.loads(session.final_plan_json)
            if not isinstance(plan_data, dict):
                return "Không rõ", session.initial_detection, "N/A"
        except json.JSONDecodeError:
            return "Lỗi JSON", session.initial_detection, "N/A"

        main_diagnosis = session.initial_detection
        risk_value = "N/A"
        plan_type = session.plan_type
        
        if plan_type == "fertilizer":
            plan_name_vn = "Bón phân"
            summary = plan_data.get("main_summary", "Kế hoạch Bón phân")
            main_diagnosis = f"Bón phân: {str(summary).split('.')[0].strip()}"
            risk_value = "Cố định" 
        
        elif plan_type == "water":
            plan_name_vn = "Quản lý nước"
            recommendation = plan_data.get("main_recommendation", "Tư vấn nước")
            main_diagnosis = f"Nước: {str(recommendation).strip()}"
            risk_value = "Điều chỉnh" 
        
        elif plan_type == "treatment":
            plan_name_vn = "Giám sát/Xử lý"
            analysis_data = plan_data.get("analysis", {})
            
            if isinstance(analysis_data, dict):
                risk_assessment = analysis_data.get("risk_assessment", "")
                if risk_assessment:
                    first_sentence = risk_assessment.split('.')[0].strip()
                    risk_value = first_sentence if len(first_sentence) < 30 else "Đánh giá Rủi ro"
            
        else:
            plan_name_vn = "Không rõ"
            
        return plan_name_vn, main_diagnosis, risk_value
