from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

farm_management_bp = Blueprint('farm_management_api', __name__)

@farm_management_bp.route('/fertilizer-plan', methods=['GET'])
@jwt_required()
def get_fertilizer_plan():
    """Tạo và trả về một kế hoạch bón phân chi tiết."""
    nutrient_agent = current_app.nutrient_agent
    current_user_id = get_jwt_identity()
    
    result = nutrient_agent.create_fertilization_plan(farmer_id=current_user_id)
    
    if "error" in result:
        return jsonify(result), 500
        
    return jsonify(result.get("plan")) 

@farm_management_bp.route('/water-plan', methods=['GET'])
@jwt_required()
def get_water_plan():
    """Tạo và trả về kế hoạch quản lý nước, có sử dụng dữ liệu IoT."""
    water_agent = current_app.water_agent
    iot_service = current_app.iot_service
    current_user_id = get_jwt_identity()

    user, farm = water_agent._get_user_and_farm(current_user_id)
    if not farm:
        return jsonify({"error": "Không tìm thấy nông trại để lấy dữ liệu IoT."}), 404
    
    iot_data = iot_service.get_latest_data(farm.id)
    
    result = water_agent.create_water_management_plan(farmer_id=current_user_id, iot_data=iot_data)

    if "error" in result:
        return jsonify(result), 500
    
    plan_data = result.get("plan", {}) 

    response_data = {
        "main_recommendation": plan_data.get("main_recommendation", "Không có đề xuất nào."),
        "reason": plan_data.get("reason", ""),
        "three_day_plan": plan_data.get("three_day_plan", {}),
        "current_assessment": plan_data.get("current_assessment", "")
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
    
    qa_session = current_app.analysis_repo.get_or_create_qa_session(farm.id)
    if qa_session:
        current_app.analysis_repo.save_qa_message(
            qa_session.id, question, answer_obj.get('answer', '')
        )
    
    return jsonify(answer_obj)

