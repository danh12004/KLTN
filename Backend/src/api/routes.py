from flask import Blueprint, request, jsonify, current_app
import uuid
import os
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.entity.models import User, Farm, UserSettings, AnalysisSession, db
from datetime import datetime 
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/my-farm', methods=['GET'])
@jwt_required()
def get_my_farm():
    try:
        current_user_id = get_jwt_identity()
        user = current_app.user_repo.get_user_with_farm(int(current_user_id))

        if not user:
            return jsonify({"error": "Không tìm thấy người dùng."}), 404

        farm = user.farms.first()

        if not farm:
            return jsonify({"error": "Người dùng này chưa có thông tin nông trại."}), 404
        
        return jsonify({
            "id": farm.id,
            "name": farm.name,
            "farmer_name": user.full_name,
            "province": farm.province,
            "area_ha": farm.area_ha,
            "planting_date": farm.planting_date.strftime('%Y-%m-%d') if farm.planting_date else None
        })
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy thông tin nông trại: {e}")
        return jsonify({"error": "Lỗi server nội bộ khi truy vấn dữ liệu."}), 500

@api_bp.route('/automated-analysis', methods=['POST'])
def automated_analysis_endpoint():
    monitoring_agent = current_app.monitoring_agent
    pending_plans = current_app.pending_plans

    data = request.get_json()
    if not data or 'farmer_id' not in data:
        return jsonify({"error": "Request thiếu farmer_id"}), 400
    
    farmer_id = data['farmer_id']
    result = monitoring_agent.run_single_automated_analysis(farmer_id)

    if "error" in result:
        return jsonify(result), 500

    conversation_id = result.get("session_id")
    plan = result.get("plan")
    
    if not conversation_id or not plan:
        return jsonify({"error": "Lỗi hệ thống: Không thể tạo phiên phân tích."}), 500

    pending_plans[conversation_id] = plan

    return jsonify({
        "conversation_id": conversation_id,
        "plan": plan
    })

@api_bp.route('/chat', methods=['POST'])
def handle_chat_message():
    pending_plans = current_app.pending_plans
    decision_agent = current_app.decision_agent

    data = request.get_json()
    if not data or 'conversation_id' not in data or 'message' not in data:
        return jsonify({"error": "Request thiếu conversation_id hoặc message"}), 400
        
    conversation_id = data['conversation_id']
    user_message = data['message']
    
    current_plan = pending_plans.get(conversation_id)
    if not current_plan:
        return jsonify({"error": "Phiên làm việc đã hết hạn hoặc không tồn tại."}), 404

    updated_plan = decision_agent.update_plan_from_feedback(current_plan, user_message)

    if "error" in updated_plan:
        return jsonify(updated_plan)

    pending_plans[conversation_id] = updated_plan

    save_result = current_app.analysis_repo.save_chat_interaction(
        conversation_id, user_message, updated_plan
    )

    if "error" in save_result:
        return jsonify(save_result), 500
    
    return jsonify({
        "conversation_id": conversation_id,
        "plan": updated_plan
    })

@api_bp.route('/ask', methods=['POST'])
def ask_question():
    qa_agent = current_app.qa_agent
    data = request.get_json()
    if not data or 'farmer_id' not in data or 'question' not in data:
        return jsonify({"error": "Request thiếu farmer_id hoặc question"}), 400
    
    farmer_id = data['farmer_id']
    question = data['question']

    try:
        user = current_app.user_repo.get_user_with_farm(int(farmer_id))
        if not user or not user.farms:
            return jsonify({"error": "Không tìm thấy thông tin nông trại cho người dùng này."}), 404
        
        farm = user.farms.first() 
        
        farmer_info = {
            "farmer_id": user.id,
            "full_name": user.full_name,
            "farm_name": farm.name,
            "province": farm.province,
            "area_ha": farm.area_ha,
            "planting_date": farm.planting_date.strftime('%Y-%m-%d') if farm.planting_date else None,
            "soil_ph": farm.soil_ph
        }

    except Exception as e:
        current_app.logger.error(f"Lỗi khi truy vấn thông tin nông dân: {e}")
        return jsonify({"error": "Lỗi server khi lấy dữ liệu nông hộ."}), 500

    answer_obj = qa_agent.answer_question(farmer_info, question)
    qa_session = current_app.analysis_repo.get_or_create_qa_session(farm.id)
    if qa_session:
        current_app.analysis_repo.save_qa_message(
            qa_session.id, question, answer_obj.get('answer', '')
        )
    
    return jsonify(answer_obj)

@api_bp.route('/execute', methods=['POST'])
def execute_treatment_plan():
    pending_plans = current_app.pending_plans
    action_agent = current_app.action_agent
    analysis_repo = current_app.analysis_repo 

    data = request.get_json()
    if not data or 'conversation_id' not in data:
        return jsonify({"error": "Request thiếu conversation_id"}), 400
        
    conversation_id = data['conversation_id']
    plan_to_execute = pending_plans.get(conversation_id)
    
    if not plan_to_execute:
        session = analysis_repo.get_session_by_id(conversation_id)
        if session and session.final_plan_json:
            plan_to_execute = json.loads(session.final_plan_json)
        else:
            return jsonify({"error": "Phiên làm việc đã hết hạn hoặc không tồn tại."}), 404

    action_details = plan_to_execute.get("action_details_for_system")
    if not action_details:
        return jsonify({"error": "Kế hoạch không có thông tin để thực thi."}), 400
        
    farmer_id = action_details.get("farmer_id")
    drug_info = action_details.get("drug_info")
    
    result = action_agent.execute_spraying(farmer_id, drug_info)

    if result and "error" in result:
        return jsonify(result), 500

    analysis_repo.update_session_status(conversation_id, "executed")
    
    if conversation_id in pending_plans:
        del pending_plans[conversation_id]
    
    return jsonify(result)

@api_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_settings():
    current_user_id = get_jwt_identity()
    settings = current_app.user_repo.get_settings_by_user_id(current_user_id)
    return jsonify({
        "enabled": settings.notification_enabled,
        "interval": settings.notification_interval_hours 
    })

@api_bp.route('/settings', methods=['POST'])
@jwt_required()
def update_settings():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    result = current_app.user_repo.update_user_settings(
        user_id=int(current_user_id),
        settings_data=data.get('notification_settings', {}),
        farm_data=data.get('farm_info', {})
    )

    if "error" in result:
        return jsonify(result), 500
    
    return jsonify({"message": "Cài đặt đã được cập nhật thành công!"})
    
@api_bp.route('/notifications/latest', methods=['GET'])
@jwt_required()
def get_latest_notification():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or not user.farms.first():
        return jsonify({"error": "Không tìm thấy nông trại."}), 404
    
    farm = user.farms.first()
    latest_session = current_app.analysis_repo.get_latest_session_for_farm(farm.id)
    
    if not latest_session or not latest_session.final_plan_json:
        return jsonify({"error": "Không có thông báo mới nào."}), 404

    conversation_id = latest_session.id 
    plan = json.loads(latest_session.final_plan_json)

    current_app.pending_plans[conversation_id] = plan
    
    return jsonify({
        "conversation_id": conversation_id,
        "plan": plan
    })

@api_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or not user.farms.first():
        return jsonify([]), 200 
    
    farm = user.farms.first()
    sessions = current_app.analysis_repo.get_all_sessions_for_farm(farm.id)

    history_list = []
    for session in sessions:
        plan = json.loads(session.final_plan_json) if session.final_plan_json else {}
        risk = plan.get("analysis", {}).get("risk_assessment", "Không rõ")
        
        history_list.append({
            "id": session.id,
            "date": session.created_at.strftime('%Y-%m-%d'),
            "disease": session.initial_detection,
            "risk": risk.split('.')[0], 
            "status": "Đã xử lý"
        })
        
    return jsonify(history_list)