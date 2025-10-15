from flask import request
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.entity.models import User
from ..tasks import scheduled_monitoring_task 
import json

user_bp = Blueprint('user_api', __name__)

@user_bp.route('/my-farm', methods=['GET'])
@jwt_required()
def get_my_farm():
    current_user_id = get_jwt_identity()
    user = current_app.user_repo.get_user_with_farm(int(current_user_id))
    if not user or not user.farms.first():
        return jsonify({"error": "Không tìm thấy thông tin nông trại."}), 404
    
    farm = user.farms.first()
    return jsonify({
        "id": farm.id, "name": farm.name, "farmer_name": user.full_name,
        "province": farm.province, "area_ha": farm.area_ha,
        "planting_date": farm.planting_date.strftime('%Y-%m-%d') if farm.planting_date else None
    })

@user_bp.route('/settings', methods=['GET', 'POST'])
@jwt_required()
def handle_settings():
    current_user_id = get_jwt_identity()
    
    if request.method == 'GET':
        settings = current_app.user_repo.get_settings_by_user_id(current_user_id)
        return jsonify({
            "enabled": settings.notification_enabled,
            "interval": settings.notification_interval_hours 
        })
    
    data = request.get_json()
    settings_data = data.get('notification_settings', {})
    
    result = current_app.user_repo.update_user_settings(
        user_id=current_user_id,
        settings_data=settings_data,
        farm_data=data.get('farm_info', {})
    )
    if "error" in result:
        return jsonify(result), 500

    scheduler = current_app.scheduler
    job_id = f'monitoring_job_for_user_{current_user_id}'

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"Đã xóa job giám sát cũ '{job_id}' để cập nhật.")

    if settings_data.get('enabled'):
        new_interval = settings_data.get('interval', 24)
        scheduler.add_job(
            id=job_id,
            func=scheduled_monitoring_task,
            args=[current_app._get_current_object(), current_user_id],
            trigger='interval',
            hours=new_interval
        )
        print(f"Đã lên lịch lại job '{job_id}' với tần suất {new_interval} giờ.")
    else:
        print(f"Người dùng {current_user_id} đã tắt giám sát. Không tạo job mới.")
        
    return jsonify({"message": "Cài đặt và lịch trình giám sát đã được cập nhật thành công!"})

@user_bp.route('/notifications/latest', methods=['GET'])
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
    current_app.pending_plans[str(conversation_id)] = plan
    
    return jsonify({"conversation_id": conversation_id, "plan": plan})

@user_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or not user.farms.first():
        return jsonify([]), 200
    
    farm = user.farms.first()
    sessions = current_app.analysis_repo.get_all_sessions_for_farm(farm.id)
    
    history_list = [
        {
            "id": s.id, "date": s.created_at.strftime('%Y-%m-%d'),
            "disease": s.initial_detection,
            "risk": (json.loads(s.final_plan_json).get("analysis", {}).get("risk_assessment", "Không rõ")).split('.')[0],
            "status": "An toàn" if s.initial_detection == "Khỏe mạnh" else "Đã xử lý"
        } for s in sessions if s.final_plan_json
    ]
    return jsonify(history_list)
