import json
import datetime
from dateutil import parser
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.logging.logger import logger 
import time

treatment_bp = Blueprint('treatment_api', __name__)

TASK_DURATION_SCHEDULED_SECONDS = 300

@treatment_bp.route('/treatment-plan', methods=['GET'])
@jwt_required()
def get_treatment_plan():
    """
    Tạo (hoặc lấy) một kế hoạch điều trị sâu bệnh/vấn đề, tương tự như get_fertilizer_plan.
    Sử dụng monitoring_agent để chạy phân tích và tạo kế hoạch ban đầu.
    """
    start_time = time.perf_counter()
    monitoring_agent = current_app.monitoring_agent
    iot_service = current_app.iot_service
    current_user_id = get_jwt_identity()
    
    try:
        iot_data = iot_service.get_latest_data(farm_id=current_user_id)
    except Exception as e:
        return jsonify({"msg": f"Lỗi khi lấy dữ liệu IoT: {e}"}), 500
    
    result = monitoring_agent.run_single_automated_analysis(farmer_id=current_user_id, iot_data=iot_data)
    
    end_time = time.perf_counter()  
    latency = end_time - start_time
    logger.info(f"[LATENCY] Treatment agent response time: {latency:.3f} seconds")

    if "error" in result:
        return jsonify(result), 500
    
    session_id_key = "conversation_id" if "conversation_id" in result else "session_id"
    
    response_data = {
        "conversation_id": result.get(session_id_key),
        "plan": result.get("plan"),
        "original_plan": result.get("original_plan"), 
        "status": result.get("status"),
        "main_message": (result.get("plan") or {}).get("main_message", result.get("message"))
    }

    return jsonify(response_data) 

@treatment_bp.route('/treatment-plan/update', methods=['POST'])
@jwt_required()
def update_treatment_plan():
    """
    Nhận phản hồi (chat) từ nông dân và cập nhật kế hoạch điều trị.
    Logic tương tự như /fertilizer-plan/update.
    """
    
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    user_message = data.get('user_message') 

    if not conversation_id or not user_message:
        return jsonify({"error": "Request thiếu 'conversation_id' hoặc 'user_message'"}), 400

    analysis_repo = current_app.analysis_repo
    treatment_agent = current_app.treatment_agent 
    action_agent = current_app.action_agent 
    
    session = analysis_repo.find_session_by_id(conversation_id)
    if not session or not session.final_plan_json:
        return jsonify({"error": "Phiên làm việc cho kế hoạch điều trị không tồn tại hoặc kế hoạch chưa được lưu."}), 404
    
    current_plan = json.loads(session.final_plan_json)
    
    updated_plan_dict = treatment_agent.update_plan_from_feedback(current_plan, user_message)
    
    original_status = session.status 
    
    if session.status == "Không hành động":
        logger.info(f"Kế hoạch (Điều trị) {session.id} được cập nhật thủ công, chuyển trạng thái từ 'Không hành động' sang 'Chờ xác nhận'.")

    if "error" in updated_plan_dict:
        return jsonify(updated_plan_dict), 500

    analysis_repo.update_session_plan(session, updated_plan_dict)
    session.suggested_plan_json = None
    
    if original_status == "Đang xử lý":
        logger.info(f"UPDATE_TREATMENT_PLAN: Kế hoạch {session.id} đang 'Đang xử lý'. Chạy lại execute_treatment với kế hoạch mới.")
        try:
            farmer_id = session.farm.user_id
            execution_result = action_agent.execute_spraying(farmer_id, updated_plan_dict)
            
            if execution_result and execution_result.get("status") == "success":
                exec_payload = execution_result.get("iot_payload", {})
                exec_time_str = exec_payload.get("execution_time")
                
                session.executed_payload_json = json.dumps(exec_payload, ensure_ascii=False)
                
                if exec_time_str:
                    exec_time_dt = parser.isoparse(exec_time_str)
                    session.execution_time = exec_time_dt
                    
                    if datetime.datetime.now(datetime.timezone.utc) >= exec_time_dt:
                        logger.info(f"UPDATE_TREATMENT_PLAN: Kế hoạch {session.id} cập nhật và đã đến hạn.")
                    else:
                        logger.info(f"UPDATE_TREATMENT_PLAN: Kế hoạch {session.id} cập nhật. Hạn thực thi mới: {exec_time_str}.")
                else:
                    logger.warning(f"UPDATE_TREATMENT_PLAN: Kế hoạch {session.id} cập nhật, nhưng execute_treatment không trả về time. Trạng thái: Đã xử lý.")
            
            else:
                error_msg = execution_result.get("message", "Lỗi execute_treatment")
                logger.error(f"UPDATE_TREATMENT_PLAN: Lỗi khi chạy lại execute_treatment cho {session.id}: {error_msg}")

        except Exception as e:
            logger.error(f"UPDATE_TREATMENT_PLAN: Lỗi nghiêm trọng khi chạy lại execute_treatment cho {session.id}: {e}", exc_info=True)

    analysis_repo.commit() 

    response_data = {
        "conversation_id": conversation_id,
        "plan": updated_plan_dict, 
        "original_plan": None,    
        "status": session.status,
        "main_message": updated_plan_dict.get("main_message", "Kế hoạch điều trị đã được cập nhật."),
    }

    return jsonify(response_data)

@treatment_bp.route('/treatment-plan/action', methods=['POST'])
@jwt_required()
def handle_plan_action():
    """
    Xử lý việc nông dân chọn "Chấp nhận gợi ý" hoặc "Giữ kế hoạch gốc" cho KẾ HOẠCH ĐIỀU TRỊ.
    """
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    action = data.get('action')

    if not conversation_id or not action:
        return jsonify({"error": "Thiếu 'conversation_id' hoặc 'action'"}), 400

    analysis_repo = current_app.analysis_repo
    action_agent = current_app.action_agent
    logger = current_app.logger

    session = analysis_repo.find_session_by_id(conversation_id)
    if not session:
        return jsonify({"error": "Không tìm thấy phiên làm việc"}), 404

    new_final_plan_dict = None
    message = ""
    original_status = session.status

    if action == "accept_suggestion":
        if not session.suggested_plan_json:
            return jsonify({"error": "Không có kế hoạch gợi ý để chấp nhận"}), 400

        session.final_plan_json = session.suggested_plan_json
        session.suggested_plan_json = None
        new_final_plan_dict = json.loads(session.final_plan_json)
        message = "Đã chấp nhận và cập nhật kế hoạch điều trị gợi ý."

        if original_status == "Đang xử lý":
            try:
                farmer_id = session.farm.user_id
                execution_result = action_agent.execute_spraying(farmer_id, new_final_plan_dict)

                if execution_result and execution_result.get("status") == "success":
                    exec_payload = execution_result.get("iot_payload", {})
                    exec_time_str = exec_payload.get("execution_time")

                    session.executed_payload_json = json.dumps(exec_payload, ensure_ascii=False)

                    if exec_time_str:
                        exec_time_dt = parser.isoparse(exec_time_str)
                        session.execution_time = exec_time_dt

                        if datetime.datetime.now(datetime.timezone.utc) >= exec_time_dt:
                            logger.info(f"TREATMENT_PLAN_ACTION: Kế hoạch {session.id} đã đến hạn")
                        else:
                            logger.info(f"TREATMENT_PLAN_ACTION: Kế hoạch {session.id} cập nhật. Hạn thực thi mới: {exec_time_str}.")
                    else:
                        logger.warning(f"TREATMENT_PLAN_ACTION: Không có execution_time trả về.")

                else:
                    error_msg = execution_result.get("message", "Lỗi execute_treatment")
                    logger.error(f"TREATMENT_PLAN_ACTION: Lỗi khi chạy execute_spraying cho {session.id}: {error_msg}")

            except Exception as e:
                logger.error(f"TREATMENT_PLAN_ACTION: Lỗi nghiêm trọng khi chạy execute_spraying cho {session.id}: {e}", exc_info=True)

    elif action == "reject_suggestion":
        if not session.suggested_plan_json:
            new_final_plan_dict = json.loads(session.final_plan_json)
            message = "Đã giữ lại kế hoạch điều trị gốc (không có gì thay đổi)."
        else:
            session.suggested_plan_json = None
            new_final_plan_dict = json.loads(session.final_plan_json)
            message = "Đã từ chối gợi ý và giữ lại kế hoạch điều trị gốc."

    else:
        return jsonify({"error": "Hành động không hợp lệ"}), 400

    analysis_repo.commit()

    response_data = {
        "conversation_id": conversation_id,
        "plan": new_final_plan_dict,
        "original_plan": None,
        "status": session.status,
        "main_message": message,
    }

    return jsonify(response_data)

