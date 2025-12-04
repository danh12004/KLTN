import json
import datetime              
from dateutil import parser  
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.logging.logger import logger
import time

farm_management_bp = Blueprint('farm_management_api', __name__)

TASK_DURATION_SCHEDULED_SECONDS = 300

@farm_management_bp.route('/fertilizer-plan', methods=['GET'])
@jwt_required()
def get_fertilizer_plan():
    """Tạo và trả về một kế hoạch bón phân chi tiết, kèm session_id."""
    start_time = time.perf_counter()
    nutrient_agent = current_app.nutrient_agent
    iot_service = current_app.iot_service
    current_user_id = get_jwt_identity()
    
    try:
        iot_data = iot_service.get_latest_data(farm_id=current_user_id,)
    except Exception as e:
        return jsonify({"msg": f"Lỗi khi lấy dữ liệu IoT: {e}"}), 500
    
    result = nutrient_agent.create_fertilization_plan(farmer_id=current_user_id, iot_data=iot_data)
    
    end_time = time.perf_counter()  
    latency = end_time - start_time
    logger.info(f"[LATENCY] Fertilizer agent response time: {latency:.3f} seconds")
    
    if "error" in result:
        return jsonify(result), 500
        
    response_data = {
        "conversation_id": result.get("session_id"),
        "plan": result.get("plan"),
        "original_plan": result.get("original_plan"), 
        "status": result.get("status"),
        "main_message": (result.get("plan") or {}).get("main_message", result.get("message"))
    }
    
    return jsonify(response_data) 

@farm_management_bp.route('/fertilizer-plan/update', methods=['POST'])
@jwt_required()
def update_fertilizer_plan():
    """Nhận phản hồi từ nông dân và cập nhật kế hoạch bón phân."""
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    user_message = data.get('user_message')

    if not conversation_id or not user_message:
        return jsonify({"error": "Request thiếu 'conversation_id' hoặc 'user_message'"}), 400

    analysis_repo = current_app.analysis_repo
    nutrient_agent = current_app.nutrient_agent
    action_agent = current_app.action_agent 
    
    session = analysis_repo.find_session_by_id(conversation_id)
    if not session or not session.final_plan_json:
        return jsonify({"error": "Phiên làm việc cho kế hoạch bón phân không tồn tại hoặc kế hoạch chưa được lưu."}), 404
    
    current_plan = json.loads(session.final_plan_json)
    
    updated_plan_dict = nutrient_agent.update_plan_from_feedback(current_plan, user_message)
    
    original_status = session.status 
    
    if session.status == "Không hành động":
        logger.info(f"Kế hoạch {session.id} được cập nhật thủ công, chuyển trạng thái từ 'Không hành động' sang 'Chờ xác nhận'.")

    if "error" in updated_plan_dict:
        return jsonify(updated_plan_dict), 500

    analysis_repo.update_session_plan(session, updated_plan_dict)
    session.suggested_plan_json = None
    
    if original_status == "Đang xử lý":
        logger.info(f"UPDATE_PLAN: Kế hoạch {session.id} đang 'Đang xử lý'. Chạy lại execute_fertilizing với kế hoạch mới.")
        try:
            farmer_id = session.farm.user_id
            execution_result = action_agent.execute_fertilizing(farmer_id, updated_plan_dict)
            
            if execution_result and execution_result.get("status") == "success":
                exec_payload = execution_result.get("iot_payload", {})
                exec_time_str = execution_result.get("execution_time")
                
                session.executed_payload_json = json.dumps(exec_payload, ensure_ascii=False)
                
                if exec_time_str:
                    exec_time_dt = parser.isoparse(exec_time_str)
                    session.execution_time = exec_time_dt
                    
                    if datetime.datetime.now(datetime.timezone.utc) >= exec_time_dt:
                        logger.info(f"UPDATE_PLAN: Kế hoạch {session.id} cập nhật và đã đến hạn.")
                    else:
                        logger.info(f"UPDATE_PLAN: Kế hoạch {session.id} cập nhật. Hạn thực thi mới: {exec_time_str}.")
                else:
                    logger.warning(f"UPDATE_PLAN: Kế hoạch {session.id} cập nhật, nhưng execute_fertilizing không trả về time. Trạng thái: Đã xử lý.")
            
            else:
                error_msg = execution_result.get("message", "Lỗi execute_fertilizing")
                logger.error(f"UPDATE_PLAN: Lỗi khi chạy lại execute_fertilizing cho {session.id}: {error_msg}")

        except Exception as e:
            logger.error(f"UPDATE_PLAN: Lỗi nghiêm trọng khi chạy lại execute_fertilizing cho {session.id}: {e}", exc_info=True)

    analysis_repo.commit() 

    response_data = {
        "conversation_id": conversation_id,
        "plan": updated_plan_dict, 
        "original_plan": None,    
        "status": session.status,
        "main_message": updated_plan_dict.get("main_message", "Kế hoạch đã được cập nhật."),
    }

    return jsonify(response_data)

@farm_management_bp.route('/fertilizer-plan/action', methods=['POST'])
@jwt_required()
def handle_plan_action():
    """
    Xử lý việc nông dân chọn "Chấp nhận gợi ý" hoặc "Giữ kế hoạch gốc" cho KẾ HOẠCH ĐIỀU TRỊ.
    action: "accept_suggestion" | "reject_suggestion"
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
                            logger.info(f"TREATMENT_PLAN_ACTION: Kế hoạch {session.id} đã đến hạn.")
                        else:
                            logger.info(f"TREATMENT_PLAN_ACTION: Kế hoạch {session.id} cập nhật. Hạn thực thi mới: {exec_time_str}.")
                    else:
                        logger.warning(f"TREATMENT_PLAN_ACTION: Không có execution_time trả về. Giữ nguyên trạng thái.")

                else:
                    error_msg = execution_result.get("message", "Lỗi execute_spraying")
                    logger.error(f"TREATMENT_PLAN_ACTION: Lỗi khi chạy execute_spraying cho {session.id}: {error_msg}")

            except Exception as e:
                logger.error(f"TREATMENT_PLAN_ACTION: Lỗi nghiêm trọng khi chạy execute_spraying cho {session.id}: {e}", exc_info=True)

    elif action == "reject_suggestion":
        if not session.suggested_plan_json:
            new_final_plan_dict = json.loads(session.final_plan_json)
            message = "Đã giữ lại kế hoạch điều trị gốc (không có gì thay đổi)."
            logger.error(f"TREATMENT_PLAN_ACTION: Không đổi kế hoạch")
        else:
            session.suggested_plan_json = None
            new_final_plan_dict = json.loads(session.final_plan_json)
            message = "Đã từ chối gợi ý và giữ lại kế hoạch điều trị gốc."
            logger.error(f"TREATMENT_PLAN_ACTION: Xóa kế hoạch gợi ý mới")

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

@farm_management_bp.route('/water-plan', methods=['GET'])
@jwt_required()
def get_water_plan():
    """Tạo và trả về kế hoạch quản lý nước, có sử dụng dữ liệu IoT."""
    start_time = time.perf_counter()
    water_agent = current_app.water_agent
    iot_service = current_app.iot_service
    current_user_id = get_jwt_identity()

    user, farm = water_agent._get_user_and_farm(current_user_id)
    if not farm:
        return jsonify({"error": "Không tìm thấy nông trại để lấy dữ liệu IoT."}), 404
    
    iot_data = iot_service.get_latest_data(farm.id)
    
    result = water_agent.create_water_management_plan(farmer_id=current_user_id, iot_data=iot_data)
    
    end_time = time.perf_counter()  
    latency = end_time - start_time
    logger.info(f"[LATENCY] Water agent response time: {latency:.3f} seconds")

    if "error" in result:
        return jsonify(result), 500
    
    plan_data = result.get("plan", {}) 
    session_id = result.get("session_id")
    
    response_data = {
        "conversation_id": session_id,
        "main_recommendation": plan_data.get("main_recommendation", "Không có đề xuất nào."),
        "reason": plan_data.get("reason", ""),
        "water_amount_detail": plan_data.get("water_amount_detail", ""),
        "three_day_plan": plan_data.get("three_day_plan", {}),
        "current_assessment": plan_data.get("current_assessment", "")
    }
    
    return jsonify(response_data)

@farm_management_bp.route('/water-plan/update', methods=['POST'])
@jwt_required()
def update_water_plan():
    """Nhận phản hồi từ nông dân và cập nhật kế hoạch quản lý nước."""
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    user_message = data.get('user_message')

    if not conversation_id or not user_message:
        return jsonify({"error": "Request thiếu 'conversation_id' hoặc 'user_message'"}), 400

    analysis_repo = current_app.analysis_repo
    water_agent = current_app.water_agent
    
    session = analysis_repo.find_session_by_id(conversation_id)
    if not session or not session.final_plan_json:
        return jsonify({"error": "Phiên làm việc không tồn tại hoặc không có kế hoạch."}), 404
    
    current_plan = json.loads(session.final_plan_json)
    
    updated_plan_dict = water_agent.update_plan_from_feedback(current_plan, user_message)

    if "error" in updated_plan_dict:
        return jsonify(updated_plan_dict), 500

    analysis_repo.update_session_plan(session, updated_plan_dict)
    analysis_repo.commit()

    response_data = {
        "conversation_id": conversation_id,
        "main_recommendation": updated_plan_dict.get("main_recommendation", "Không có đề xuất nào."),
        "reason": updated_plan_dict.get("reason", ""),
        "water_amount_detail": updated_plan_dict.get("water_amount_detail", ""), 
        "three_day_plan": updated_plan_dict.get("three_day_plan", {}),
        "current_assessment": updated_plan_dict.get("current_assessment", "")
    }

    return jsonify(response_data)


@farm_management_bp.route('/iot-data', methods=['GET'])
@jwt_required()
def get_iot_data():
    """Cung cấp dữ liệu cảm biến IoT mới nhất cho nông trại của người dùng."""
    iot_service = current_app.iot_service
    current_user_id = get_jwt_identity()
    
    user_repo = current_app.user_repo
    user = user_repo.get_user_with_farm(int(current_user_id)) 
    if not user or not user.farms.first():
        return jsonify({"error": "Không tìm thấy thông tin nông trại."}), 404
        
    farm = user.farms.first()
    
    iot_data = iot_service.get_latest_data(farm.id)
    
    return jsonify(iot_data)


@farm_management_bp.route('/ask', methods=['POST'])
@jwt_required()
def ask_question():
    """Endpoint cho chức năng hỏi đáp chung."""
    start_time = time.perf_counter()
    qa_agent = current_app.qa_agent
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    question = data.get('question')
    if not question:
        return jsonify({"error": "Request thiếu 'question'"}), 400
    
    user = current_app.user_repo.get_user_with_farm(int(current_user_id))
    if not user or not user.farms.first():
        return jsonify({"error": "Không tìm thấy thông tin nông trại."}), 404
    
    farm = user.farms.first() 
    farmer_info = {
        "farmer_id": user.id, "full_name": user.full_name, "farm_name": farm.name,
        "province": farm.province, "area_ha": farm.area_ha,
        "planting_date": farm.planting_date.strftime('%Y-%m-%d') if farm.planting_date else None,
        "soil_ph": getattr(farm, 'soil_ph', None)
    }

    answer_obj = qa_agent.answer_question(farmer_info, question)
    
    end_time = time.perf_counter()  
    latency = end_time - start_time
    logger.info(f"[LATENCY] QA agent response time: {latency:.3f} seconds")
    
    qa_session = current_app.analysis_repo.get_or_create_qa_session(farm.id)
    if qa_session:
        current_app.analysis_repo.save_qa_message(
            qa_session.id, question, answer_obj.get('answer', '')
        )
    
    return jsonify(answer_obj)
