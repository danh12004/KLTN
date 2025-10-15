import time
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

# from src.tasks import execute_spraying_task
# from src.logging.logger import logger

treatment_bp = Blueprint('treatment_api', __name__)

@treatment_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_manually():
    """Endpoint cho phép người dùng kích hoạt phân tích thủ công."""
    monitoring_agent = current_app.monitoring_agent
    pending_plans = current_app.pending_plans
    current_user_id = get_jwt_identity()
    
    result = monitoring_agent.run_single_automated_analysis(farmer_id=current_user_id)

    if "error" in result:
        return jsonify(result), 500

    session_id = result.get("session_id")
    plan = result.get("plan")
    
    if not session_id or not plan:
        return jsonify({"error": "Lỗi hệ thống: Không thể tạo phiên phân tích."}), 500

    pending_plans[str(session_id)] = plan

    return jsonify({"conversation_id": session_id, "plan": plan})

@treatment_bp.route('/chat', methods=['POST'])
@jwt_required()
def handle_chat_message():
    """Endpoint để người dùng chat và điều chỉnh kế hoạch điều trị."""
    pending_plans = current_app.pending_plans
    treatment_agent = current_app.treatment_agent 
    data = request.get_json()
    
    session_id = data.get('conversation_id')
    user_message = data.get('message')
    
    if not session_id or not user_message:
        return jsonify({"error": "Request thiếu conversation_id hoặc message"}), 400

    current_plan = pending_plans.get(str(session_id))
    if not current_plan:
        return jsonify({"error": "Phiên làm việc đã hết hạn hoặc không tồn tại."}), 404

    updated_plan = treatment_agent.update_plan_from_feedback(current_plan, user_message)

    if "error" in updated_plan:
        return jsonify(updated_plan), 500

    pending_plans[str(session_id)] = updated_plan
    current_app.analysis_repo.save_chat_interaction(session_id, user_message, updated_plan)
    
    return jsonify({"conversation_id": session_id, "plan": updated_plan})


@treatment_bp.route('/execute', methods=['POST'])
@jwt_required()
def execute_plan():
    """
    Endpoint để xác nhận và thực thi kế hoạch một cách ĐỒNG BỘ.
    """
    pending_plans = current_app.pending_plans
    action_agent = current_app.action_agent
    analysis_repo = current_app.analysis_repo 
    
    data = request.get_json()
    session_id = data.get('conversation_id')

    if not session_id:
        return jsonify({"error": "Request thiếu conversation_id"}), 400
        
    plan_to_execute = pending_plans.get(str(session_id))
    
    if not plan_to_execute:
        session = analysis_repo.find_session_by_id(session_id)
        if session and session.plan:
            plan_to_execute = session.plan
        else:
            return jsonify({"error": "Phiên làm việc đã hết hạn hoặc không tồn tại."}), 404

    action_details = plan_to_execute.get("action_details_for_system")
    if not action_details:
        return jsonify({"error": "Kế hoạch không có thông tin để thực thi."}), 400
        
    result = action_agent.execute_spraying(
        action_details.get("farmer_id"), 
        action_details.get("plan_context", {}).get("treatment_plan", {}).get("drug_info", {})
    )

    if "error" in result:
        return jsonify(result), 500

    analysis_repo.update_session_status(session_id, "Đã xử lý")
    analysis_repo.commit()
    
    if str(session_id) in pending_plans:
        del pending_plans[str(session_id)]
    
    return jsonify(result)