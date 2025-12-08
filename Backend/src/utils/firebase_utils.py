import time
from datetime import datetime
from src.logging.logger import logger 
from firebase_admin import db

def push_execution_to_firebase(session_id, payload, plan_type):
    """
    Đẩy dữ liệu executed_payload_data lên Firebase theo session + loại kế hoạch.
    """
    try:
        import time
        timestamp = int(time.time()) 
        current_date = datetime.now().strftime("%Y%m%d")   

        ref = db.reference(f"executions/{current_date}/{plan_type}/{timestamp}")
        ref.set({
            "session_id": session_id,
            "payload": payload  
        })
        logger.info(f"[FIREBASE] Đã gửi dữ liệu cho {session_id} ({plan_type}) [{timestamp}]")
    except Exception as e:
        logger.error(f"[FIREBASE] Lỗi khi gửi dữ liệu: {e}")
        
def push_follow_up_to_firebase(session_id, lat, lon):
    """
    Đẩy yêu cầu theo dõi (Follow-up) lên Firebase, bao gồm tọa độ
    để thiết bị IoT/Drone quay lại vị trí đã thực thi để thu thập dữ liệu mới (ảnh/cảm biến).
    """
    try:
        timestamp = int(time.time()) 
        ref = db.reference(f"follow_up_requests/{session_id}/{timestamp}")
        
        follow_up_payload = {
            "session_id": session_id,
            "latitude": lat,
            "longitude": lon,
            "request_time": timestamp,
            "status": "pending_image_capture"
        }
        
        ref.set(follow_up_payload)
        logger.info(f"[FIREBASE] Đã gửi yêu cầu theo dõi (Follow-up) cho Session {session_id} tại Lat={lat}, Lon={lon}.")
        
    except Exception as e:
        logger.error(f"[FIREBASE] Lỗi khi gửi yêu cầu theo dõi: {e}")