import time
import threading
import json
import datetime
from dateutil import parser
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from src.utils.firebase_utils import push_execution_to_firebase, push_follow_up_to_firebase
from src.logging.logger import logger

plan_bp = Blueprint('plan_api', __name__)

TASK_DURATION_WATER_SECONDS = 10     
TASK_DURATION_SCHEDULED_SECONDS = 10

FOLLOW_UP_DAYS_TREATMENT = 7  
FOLLOW_UP_DAYS_FERTILIZER = 10

def _execute_task_in_background(app, session_id, plan_type):
    """
    Hàm chạy nền để mô phỏng tác vụ tốn thời gian.
    Tích hợp logic Firebase Push và Time Delay dựa trên plan_type.
    """
    
    with app.app_context():
        logger = app.logger
        analysis_repo = app.analysis_repo
        action_agent = app.action_agent

        session = analysis_repo.find_session_by_id(session_id)
        if not session:
            logger.error(f"BACKGROUND_TASK: Không tìm thấy session {session_id}.")
            return
        if session.status in ["Đã xử lý", "Lỗi"]:
            logger.warning(f"BACKGROUND_TASK: Session {session_id} đã có trạng thái '{session.status}'. Bỏ qua thực thi.")
            return

        if plan_type == 'water':
            logger.info(f"BACKGROUND_TASK: Giả lập xử lý water {session_id} ({TASK_DURATION_WATER_SECONDS}s)...")
            time.sleep(TASK_DURATION_WATER_SECONDS) 
        else:
            logger.info(f"BACKGROUND_TASK: Bắt đầu thực thi (Loại: {plan_type}) session {session_id}.")

        session = analysis_repo.find_session_by_id(session_id)
        if not session or session.status != "Đang xử lý":
            logger.warning(f"BACKGROUND_TASK: Session {session_id} đã thay đổi trạng thái trong lúc chờ. Bỏ qua.")
            return

        if not session.final_plan_json:
            logger.error(f"BACKGROUND_TASK: Session {session_id} không có kế hoạch.")
            return

        try:
            plan_to_execute = json.loads(session.final_plan_json)
            logger.info(f"\n[DEBUG] ====== JSON KẾ HOẠCH NHẬN ĐƯỢC ======\n{json.dumps(plan_to_execute, ensure_ascii=False, indent=4)}\n===========================================")
        except Exception as e:
            logger.error(f"[DEBUG] Lỗi khi parse JSON từ session.final_plan_json: {e}")
            return

        farmer_id = session.farm.user_id
        execution_result = None

        try:
            if plan_type == 'treatment':
                logger.info("[DEBUG] >> Gọi execute_spraying()")
                execution_result = action_agent.execute_spraying(farmer_id, plan_to_execute)
            elif plan_type == 'fertilizer':
                logger.info("[DEBUG] >> Gọi execute_fertilizing()")
                execution_result = action_agent.execute_fertilizing(farmer_id, plan_to_execute)
            elif plan_type == 'water':
                logger.info("[DEBUG] >> Gọi execute_watering()")
                execution_result = action_agent.execute_watering(farmer_id, plan_to_execute)
            else:
                logger.warning(f"BACKGROUND_TASK: Loại kế hoạch không xác định: {plan_type} cho session {session_id}.")
                session.status = f"Lỗi: Loại kế hoạch '{plan_type}' không hợp lệ"
                analysis_repo.commit()
                return

            if execution_result and execution_result.get("status") == "success":
                executed_payload_data = execution_result.get("iot_payload", {})
                
                session.executed_payload_json = json.dumps(executed_payload_data, ensure_ascii=False)

                if plan_type in ['fertilizer', 'treatment']:
                    
                    execution_time_str = executed_payload_data.get("execution_time")
                    
                    try:
                        if execution_time_str:
                            execution_dt = parser.isoparse(execution_time_str)
                            execution_dt = execution_dt.astimezone(datetime.timezone.utc)
                            now_dt = datetime.datetime.now(datetime.timezone.utc)

                            if execution_dt < now_dt:
                                logger.warning(f"BACKGROUND_TASK: Kế hoạch {plan_type} cho session {session_id} đã quá hạn (Hạn: {execution_time_str}).")
                                session.status = "Kế hoạch quá hạn"
                                analysis_repo.commit()
                                return
                    except:
                        session.status = "Lỗi: execution_time không hợp lệ"
                        analysis_repo.commit()
                        logger.error("execution_time không hợp lệ")
                        return
                    
                    if execution_time_str:
                        try:
                            execution_time_dt = parser.isoparse(execution_time_str)
                            if execution_time_dt.tzinfo is None:
                                execution_time_dt = execution_time_dt.replace(tzinfo=datetime.timezone.utc)
                            session.execution_time = execution_time_dt
                            
                            if plan_type == 'treatment':
                                follow_up_days = FOLLOW_UP_DAYS_TREATMENT
                            else:   
                                follow_up_days = FOLLOW_UP_DAYS_FERTILIZER
                            
                            follow_up_time_dt = execution_time_dt + datetime.timedelta(days=follow_up_days)

                            session.follow_up_time = follow_up_time_dt 
                            session.follow_up_status = "Chờ theo dõi"

                            if datetime.datetime.now(datetime.timezone.utc) >= execution_time_dt:
                                logger.info(f"BACKGROUND_TASK: Gửi dữ liệu lên firebase và chờ {TASK_DURATION_SCHEDULED_SECONDS}s (Đã đến hạn).")
                                push_execution_to_firebase(session_id, executed_payload_data, plan_type)
                                
                                time.sleep(TASK_DURATION_SCHEDULED_SECONDS)
                                
                                session.status = "Đã xử lý"
                                analysis_repo.commit()
                                logger.info(f"BACKGROUND_TASK: Hoàn thành & Cập nhật trạng thái 'Đã xử lý' sau khi chờ.")
                            else:
                                logger.info(f"BACKGROUND_TASK: Đã lên lịch & Lưu Payload cho session {session_id}. Hạn thực thi: {execution_time_str}.")
                        except Exception as e:
                            logger.error(f"BACKGROUND_TASK: Lỗi khi xử lý 'execution_date' từ plan {execution_time_str}: {e}")
                    else:
                        logger.warning(f"BACKGROUND_TASK: Kế hoạch không có 'execution_date'. Mặc định 'Đã xử lý'.")
                        session.status = "Đã xử lý"
                
                elif plan_type == 'water':
                    logger.info(f"BACKGROUND_TASK: Gửi dữ liệu lên firebase và chờ {TASK_DURATION_WATER_SECONDS}s (Water).")
                    push_execution_to_firebase(session_id, executed_payload_data, plan_type)
                    
                    time.sleep(TASK_DURATION_WATER_SECONDS)
                    
                    session.status = "Đã xử lý"
                    logger.info(f"BACKGROUND_TASK: Hoàn thành & Cập nhật trạng thái 'Đã xử lý' sau khi chờ 10s.")
                
            else:
                error_msg = execution_result.get("message", "Lỗi không xác định")
                logger.error(f"BACKGROUND_TASK: Lỗi khi thực thi {plan_type} cho session {session_id}: {error_msg}")

        except Exception as e:
            logger.error(f"BACKGROUND_TASK: Lỗi nghiêm trọng khi thực thi session {session_id}: {e}", exc_info=True)
        finally:
            analysis_repo.commit()

@plan_bp.route('/execute', methods=['POST'])
@jwt_required()
def execute_generic_plan():
    """
    Endpoint chung để bắt đầu thực thi một kế hoạch.
    Kiểm tra trạng thái trước khi thực thi.
    """
    data = request.get_json()
    session_id = data.get('conversation_id')
    plan_type = data.get('plan_type') 

    if not session_id or not plan_type:
        return jsonify({"error": "Request thiếu 'conversation_id' hoặc 'plan_type'"}), 400
    
    analysis_repo = current_app.analysis_repo
    session = analysis_repo.find_session_by_id(session_id)
    if not session:
        return jsonify({"error": "Phiên làm việc không tồn tại."}), 404
        
    if session.status == "Đã xử lý":
        return jsonify({
            "message": f"Kế hoạch loại '{plan_type}' (ID: {session_id}) đã được thực thi và hoàn thành trước đó.",
            "status": "already_executed"
        }), 200
    
    if session.status == "Đang xử lý":
        current_app.logger.warning(f"EXECUTE_API: Yêu cầu thực thi lại cho session {session_id} (Loại: {plan_type}) đang 'Đang xử lý'. Tiến hành chạy lại.")
    
    analysis_repo.update_session_status(session_id, "Đang xử lý")
    session.plan_type = plan_type
    analysis_repo.commit()
    
    thread = threading.Thread(
        target=_execute_task_in_background, 
        args=(current_app._get_current_object(), session_id, plan_type)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "message": "Lệnh thực thi đã được tiếp nhận và đang được xử lý.",
        "status": "accepted"
    }), 202

@plan_bp.route('/status/<session_id>', methods=['GET'])
@jwt_required()
def get_plan_status(session_id):
    """
    Endpoint để frontend poll, kiểm tra trạng thái kế hoạch.
    Tự động cập nhật 'Đã xử lý' nếu 'Đang xử lý' và đã đến hạn.
    """
    analysis_repo = current_app.analysis_repo
    session = analysis_repo.find_session_by_id(session_id)
    
    if not session:
        return jsonify({"error": "Phiên làm việc không tồn tại."}), 404

    try:
        if (session.status == "Đang xử lý" and 
            (session.plan_type == "fertilizer") and 
            hasattr(session, 'execution_time') and 
            session.execution_time):
            
            execution_time_dt = session.execution_time
            
            if datetime.datetime.now(datetime.timezone.utc) >= execution_time_dt:
                session.status = "Đã xử lý"
                analysis_repo.commit()
                current_app.logger.info(f"STATUS_POLL: Session {session_id} đã được cập nhật thành 'Đã xử lý' do đã đến hạn.")
                return jsonify({"status": "Đã xử lý", "message": "Kế hoạch vừa hoàn thành."})
        
        if (session.status == "Đang xử lý" and 
            (session.plan_type == "treatment") and 
            hasattr(session, 'execution_time') and 
            session.execution_time):
            
            execution_time_dt = session.execution_time
            
            if datetime.datetime.now(datetime.timezone.utc) >= execution_time_dt:
                session.status = "Đã xử lý"
                analysis_repo.commit()
                current_app.logger.info(f"STATUS_POLL: Session {session_id} đã được cập nhật thành 'Đã xử lý' do đã đến hạn.")
                return jsonify({"status": "Đã xử lý", "message": "Kế hoạch vừa hoàn thành."})

    except Exception as e:
        current_app.logger.error(f"STATUS_POLL: Lỗi khi kiểm tra thời gian session {session_id}: {e}")
    
    return jsonify({"status": session.status})
    
@plan_bp.route("/executed_latest", methods=["GET"])
def get_latest_executed_json():
    """
    Endpoint trả về JSON Payload thực thi gần nhất (public).
    Cho phép lọc bằng tham số query 'plan_type' (e.g., /executed_latest?plan_type=treatment).
    """
    analysis_repo = current_app.analysis_repo
    
    plan_type = request.args.get('plan_type') 
    
    latest_session = analysis_repo.find_latest_executed_session(plan_type=plan_type) 
    
    if not latest_session:
        error_msg = "Chưa có dữ liệu thực thi mới nhất"
        if plan_type:
            error_msg += f" cho loại kế hoạch '{plan_type}'"
        return jsonify({"error": error_msg}), 404

    try:
        return jsonify(json.loads(latest_session.executed_payload_json)), 200
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi parse executed_payload_json: {e}")
        return jsonify({"error": "Lỗi định dạng dữ liệu đã lưu."}), 500

@plan_bp.route('/executed_json/<session_id>', methods=['GET'])
def get_executed_json(session_id):
    """
    Endpoint trả về JSON Payload cuối cùng đã được ActionAgent trích xuất.
    Sẽ được công khai qua Ngrok.
    """
    analysis_repo = current_app.analysis_repo
    session = analysis_repo.find_session_by_id(session_id)

    if not session:
        return jsonify({"error": "Phiên làm việc không tồn tại."}), 404
    
    executed_data_json = getattr(session, 'executed_payload_json', None) 
    
    if not executed_data_json:
        return jsonify({
            "error": "Dữ liệu JSON thực thi chưa có sẵn.",
            "status": session.status
        }), 404

    try:
        return jsonify(json.loads(executed_data_json)), 200
        
    except Exception as e:
        current_app.logger.error(f"Lỗi khi parse executed_payload_json cho session {session_id}: {e}")
        return jsonify({"error": "Lỗi định dạng dữ liệu đã lưu."}), 500

def _re_evaluate_follow_up_sessions(app):
    with app.app_context():
        analysis_repo = app.analysis_repo
        logger = app.logger
        try:
            ema = app.monitoring_agent 
            iot_service = app.iot_service
        except AttributeError:
            logger.error("[SCHEDULER] Thiếu các thành phần cần thiết trong app context.")
            return

        logger.info("[SCHEDULER] Bắt đầu quét các phiên cần theo dõi lại...")
        
        try:
            sessions_for_follow_up = analysis_repo.find_sessions_pending_follow_up() 
        except Exception as e:
            logger.error(f"[SCHEDULER] Lỗi khi tìm kiếm sessions chờ theo dõi: {e}")
            return
        
        re_evaluated_count = 0

        for session in sessions_for_follow_up:
            try:
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                if not session.follow_up_time or now_utc < session.follow_up_time:
                    continue
                
                if session.follow_up_status == "Chờ theo dõi" or session.follow_up_status.startswith("Lỗi"):
                    
                    executed_payload = json.loads(session.executed_payload_json)
                    gps_data = executed_payload.get("gps_data")
                    lat = gps_data.get("lat")
                    lon = gps_data.get("lon")
                    
                    if not lat or not lon:
                        logger.warning(f"[SCHEDULER] Session {session.id}: Thiếu lat/lon. Không thể gửi yêu cầu theo dõi.")
                        session.follow_up_status = "Lỗi: Thiếu tọa độ"
                        analysis_repo.commit()
                        continue

                    push_follow_up_to_firebase(session.id, lat, lon)
                    logger.info(f"[SCHEDULER] Session {session.id}: Đã gửi yêu cầu theo dõi (lat={lat}, lon={lon}) lên Firebase.")
                    
                    session.follow_up_status = "Đang chờ ảnh"
                    analysis_repo.commit()
                    
                if session.follow_up_status == "Đang chờ ảnh":
                    mock_result = iot_service.fetch_mock_image_data(session.id, lat, lon)
                    
                    if mock_result['status'] != 'success':
                        session.follow_up_status = "Lỗi: Không nhận được ảnh"
                        analysis_repo.commit()
                        logger.error(f"[SCHEDULER] Session {session.id}: {mock_result['message']}")
                        continue

                    image_data = mock_result['image_data']
                    user = session.farm.user

                    logger.info(f"[SCHEDULER] Session {session.id}: Tiến hành Đánh giá lại bằng EMA.")
                    session.follow_up_status = "Đang đánh giá lại"
                    analysis_repo.commit() 
                    
                    latest_iot_data = iot_service.get_latest_data(session.id)
                    latest_iot_data["image_url"] = image_data
                    
                    ema_result = ema.check_risk_for_farmer(user, latest_iot_data)
                    
                    if ema_result and ema_result.get("status") == "orchestration_complete":
                        if ema_result.get("risk_detected", False):
                            session.follow_up_status = "Đã đánh giá lại - Rủi ro mới"
                            logger.info(f"[SCHEDULER] Session {session.id}: Đánh giá lại thành công. Rủi ro MỚI được phát hiện.")
                        else:
                            session.follow_up_status = "Đã hoàn thành theo dõi"
                            logger.info(f"[SCHEDULER] Session {session.id}: Đánh giá lại thành công. KHÔNG có rủi ro mới.")
                             
                        re_evaluated_count += 1
                    else:
                        session.follow_up_status = "Lỗi đánh giá lại"
                        logger.error(f"[SCHEDULER] Session {session.id}: Lỗi khi EMA đánh giá lại. Kết quả: {ema_result.get('error', 'Không xác định')}")
                        
                    analysis_repo.commit()

            except Exception as e:
                logger.error(f"[SCHEDULER] Lỗi xử lý follow-up cho session {session.id}: {e}", exc_info=True)
                session.follow_up_status = "Lỗi hệ thống"
                analysis_repo.commit()  
                
        logger.info(f"[SCHEDULER] Hoàn thành quét theo dõi. {re_evaluated_count} phiên đã được đánh giá lại.")
        return {"status": "success", "count": re_evaluated_count}
    
@plan_bp.route('/check-follow-up', methods=['POST'])
@jwt_required()
def trigger_follow_up_check():
    thread = threading.Thread(
        target=_re_evaluate_follow_up_sessions, 
        args=(current_app._get_current_object(),)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "message": "Lệnh quét theo dõi định kỳ đã được kích hoạt trong nền.",
        "status": "accepted"
    }), 202