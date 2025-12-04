import pandas as pd
from flask import request
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.entity.models import User
from ..tasks import scheduled_monitoring_task 
import json
from src.services.forecast_service import aggregate_hourly_to_daily 

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
        "province": farm.province, "area_ha": farm.area_ha, "rice_variety": farm.rice_variety, "soil_type": farm.soil_type,
        "planting_date": farm.planting_date.strftime('%Y-%m-%d') if farm.planting_date else None
    })

@user_bp.route('/all-analysis-locations', methods=['GET'])
@jwt_required()
def get_all_analysis_locations():
    current_user_id = get_jwt_identity()
    
    user = User.query.get(int(current_user_id))
        
    if not user or not user.farms.first():
        return jsonify({"error": "Không tìm thấy thông tin nông trại."}), 404
    
    farm = user.farms.first()
    sessions = current_app.analysis_repo.get_all_sessions_for_farm(farm.id)
    
    location_list = []
    
    for s in sessions:
        if not s.final_plan_json:
            continue
            
        try:
            plan_data = json.loads(s.final_plan_json)
        except json.JSONDecodeError:
            current_app.logger.error(f"Lỗi JSON trong session ID: {s.id}")
            continue

        gps_data = None
        plan_type, main_diagnosis, risk_value = current_app.analysis_repo._parse_plan_summary(s)
        if plan_type in ["Giám sát/Xử lý", "Quản lý nước", "Bón phân"]:
            action_details = plan_data.get("action_details_for_system", {})
            if isinstance(action_details, dict):
                gps_data = action_details.get("gps_data")
        
        if not gps_data and "farm_location" in plan_data:
             gps_data = plan_data.get("farm_location") 
             
        if not gps_data and "gps_data" in plan_data:
             gps_data = plan_data.get("gps_data")

        if gps_data and isinstance(gps_data, dict):
            try:
                lat = float(gps_data.get("lat"))
                lon = float(gps_data.get("lon"))
            except (ValueError, TypeError):
                continue
            
            if lat is not None and lon is not None:
                location_list.append({
                    "id": s.id,
                    "date": s.created_at.strftime('%Y-%m-%d %H:%M:%S'), 
                    "lat": lat,
                    "lon": lon,
                    "type": plan_type,\
                    "diagnosis": main_diagnosis, 
                    "status": s.status if s.status else "Hoàn thành"
                })
                
    return jsonify(location_list)

@user_bp.route('/farm-info-and-realtime', methods=['GET'])
@jwt_required()
def get_farm_info_and_realtime():
    current_user_id = get_jwt_identity()
    user = current_app.user_repo.get_user_with_farm(int(current_user_id))
    farm = user.farms.first()
    
    if not farm:
        return jsonify({"error": "Không tìm thấy thông tin nông trại."}), 404

    raw_iot_df = current_app.iot_service.get_hourly_data(farm.id, hours=1)
    
    latest_iot = None
    if not raw_iot_df.empty:
        latest_iot = raw_iot_df.tail(1).iloc[0].to_dict()
        latest_iot['timestamp'] = raw_iot_df.index.max().strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "farm_info": { 
            "id": farm.id, "name": farm.name, "farmer_name": user.full_name,
            "province": farm.province, "area_ha": farm.area_ha, 
            "planting_date": farm.planting_date.strftime('%Y-%m-%d') if farm.planting_date else None
        },
        "real_time_data": latest_iot, 
    })

@user_bp.route('/chart-and-forecast-data', methods=['GET'])
@jwt_required()
def get_chart_and_forecast_data():
    current_user_id = get_jwt_identity()
    user = current_app.user_repo.get_user_with_farm(int(current_user_id))
    farm = user.farms.first()
    
    if not farm:
        return jsonify({"chart_data": [], "forecast_start_date": None}), 200

    try:
        raw_iot_df = current_app.iot_service.get_hourly_data(farm.id, hours=192)
        
        daily_iot_df = aggregate_hourly_to_daily(raw_iot_df.copy())
        N_DAILY_HAVE = len(daily_iot_df)
        N_STEPS = current_app.forecast_service.N_STEPS 

        raw_df_for_forecast = raw_iot_df.copy()
        
        if N_DAILY_HAVE < N_STEPS:
            N_DAILY_MISSING = N_STEPS - N_DAILY_HAVE 
            
            end_time_fake = raw_iot_df.index.min().to_pydatetime()
            
            fake_raw_df = current_app.iot_service._generate_fake_history(
                end_time=end_time_fake, 
                days=N_DAILY_MISSING
            )
            
            raw_df_for_forecast = pd.concat([fake_raw_df, raw_iot_df])
            current_app.logger.warning(
                f"Bù trừ: Chỉ có {N_DAILY_HAVE} ngày thực. Đã thêm {N_DAILY_MISSING} ngày giả, tổng cộng {len(raw_df_for_forecast)} entry thô."
            )
        
        chart_history_df = raw_df_for_forecast.tail(168).reset_index().rename(columns={'timestamp': 'date'})
        chart_history_list = chart_history_df.to_dict('records')
        
        forecast_start_date = None
        combined_chart_data = chart_history_list

        try:
            forecast_df = current_app.forecast_service.get_forecast(raw_df_for_forecast.copy(), n_forecast_days=3)
            
            if not forecast_df.empty:
                forecast_list = forecast_df.reset_index().rename(columns={'index': 'date'}).to_dict('records')
                
                for item in forecast_list:
                    item['is_forecast'] = True
                    item['date'] = item['date'].strftime('%Y-%m-%d 12:00:00') 
                
                forecast_start_date = forecast_df.index.min().strftime('%Y-%m-%d 12:00:00')

                combined_chart_data.extend(forecast_list)
            else:
                current_app.logger.warning("Không đủ dữ liệu lịch sử để tạo dự báo.")

        except Exception as forecast_e:
            current_app.logger.error(f"Lỗi khi chạy dự báo: {forecast_e}")
            pass
        
        return jsonify({
            "chart_data": combined_chart_data, 
            "forecast_start_date": forecast_start_date
        })

    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy dữ liệu biểu đồ/dự báo: {e}")
        return jsonify({"chart_data": [], "forecast_start_date": None}), 500

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
        try:
            new_interval = int(settings_data.get('interval'))
        except (ValueError, TypeError):
            new_interval = 24
            
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
    
    if "fertilizer_stage_detail" in plan_data:
        plan_type = "Bón phân"
        summary = plan_data.get("main_summary", "Kế hoạch Bón phân")
        main_diagnosis = f"Bón phân: {str(summary).split('.')[0].strip()}"
        risk_value = "Cố định" 
    
    elif "main_recommendation" in plan_data:
        plan_type = "Quản lý nước"
        recommendation = plan_data.get("main_recommendation", "Tư vấn nước")
        main_diagnosis = f"Nước: {str(recommendation).strip()}"
        risk_value = "Điều chỉnh" 
    
    elif "treatment_plan" in plan_data:
        plan_type = "Giám sát/Xử lý"
        analysis_data = plan_data.get("analysis", {})
        
        if isinstance(analysis_data, dict):
            risk_assessment = analysis_data.get("risk_assessment", "")
            if risk_assessment:
                first_sentence = risk_assessment.split('.')[0].strip()
                risk_value = first_sentence if len(first_sentence) < 30 else "Đánh giá Rủi ro"
        
    else:
        plan_type = "Không rõ (Cấu trúc mới)"


    return plan_type, main_diagnosis, risk_value


@user_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or not user.farms.first():
        return jsonify([]), 200
    
    farm = user.farms.first()
    sessions = current_app.analysis_repo.get_all_sessions_for_farm(farm.id)
    
    history_list = []
    
    for s in sessions:
        plan_type, main_diagnosis, risk_value = _parse_plan_summary(s)
        
        status = s.status if s.status else ("An toàn" if s.initial_detection == "Khỏe mạnh" else "Chờ xử lý")
        
        history_list.append({
            "id": s.id, 
            "date": s.created_at.strftime('%Y-%m-%d'),
            "type": plan_type, 
            "diagnosis": main_diagnosis, 
            "risk": risk_value,
            "status": status
        })

    return jsonify(history_list[::-1])
    
@user_bp.route('/history/<session_id>', methods=['GET'])
@jwt_required()
def get_history_detail(session_id):
    """Trả về chi tiết của một bản ghi lịch sử (kế hoạch)."""
    analysis_repo = current_app.analysis_repo
    session = analysis_repo.find_session_by_id(session_id)

    if not session or not session.final_plan_json:
        return jsonify({"error": "Không tìm thấy dữ liệu kế hoạch."}), 404

    try:
        plan_data = json.loads(session.final_plan_json)
    except Exception as e:
        return jsonify({"error": f"Lỗi đọc dữ liệu: {str(e)}"}), 500

    return jsonify({
        "session_id": session.id,
        "type": session.plan_type,
        "status": session.status,
        "created_at": session.created_at.strftime("%Y-%m-%d %H:%M"),
        "plan": plan_data
    })

@user_bp.route('/notifications/latest', methods=['GET'])
@jwt_required()
def get_latest_notification():
    current_user_id = get_jwt_identity()
    user_repo = current_app.user_repo
    user = user_repo.get_user_with_farm(int(current_user_id))
    
    if not user or not user.farms.first():
        return jsonify({"error": "Không tìm thấy nông trại."}), 404

    farm = user.farms.first()
    requested_type = request.args.get('plan_type', 'treatment')

    latest_session = current_app.analysis_repo.get_latest_session_for_farm_by_type(farm.id, requested_type)
    if not latest_session:
        return jsonify({"error": f"Không có thông báo mới nào thuộc loại '{requested_type}'."}), 404

    if requested_type in ['fertilizer', 'treatment']:
        
        if not latest_session.final_plan_json:
            return jsonify({"error": f"Session ID {latest_session.id} không chứa final_plan_json."}), 404

        plan_type, _, _ = _parse_plan_summary(latest_session)

        response_data = {
            "conversation_id": latest_session.id,
            "plan_type": plan_type, 
            "status": latest_session.status,
            "final_plan_json": latest_session.final_plan_json,
            "suggested_plan_json": latest_session.suggested_plan_json 
        }
        return jsonify(response_data)
    
    if not latest_session.final_plan_json:
        return jsonify({"error": f"Session ID {latest_session.id} không chứa final_plan_json."}), 404

    try:
        plan_content = json.loads(latest_session.final_plan_json)
        if not isinstance(plan_content, dict):
            raise ValueError("Dữ liệu kế hoạch không hợp lệ.")
    except Exception as e:
        current_app.logger.error(f"Lỗi khi parse JSON cho session {latest_session.id}: {e}")
        return jsonify({"error": "Lỗi định dạng dữ liệu kế hoạch."}), 500

    plan_type, _, _ = _parse_plan_summary(latest_session)

    response_data = {
        "conversation_id": latest_session.id,
        "plan_type": plan_type,
        "status": latest_session.status,
        "status_execution": "Đã xử lý" if latest_session.status == "Đã xử lý" else "Chưa xử lý",
        **plan_content
    }

    return jsonify(response_data)

@user_bp.route('/session/<session_id>', methods=['GET'])
@jwt_required()
def get_session_details(session_id):
    analysis_repo = current_app.analysis_repo
    
    session = analysis_repo.find_session_by_id(session_id)
    if not session:
        return jsonify({"error": "Phiên làm việc không tồn tại."}), 404
        
    chat_messages = analysis_repo.get_chat_history_for_session(session_id)
    chat_history = [
        {"sender": "ai" if msg.is_ai_response else "user", "text": msg.message}
        for msg in chat_messages
    ]
    
    plan = {}
    plan_type, _, _ = _parse_plan_summary(session)

    if session.final_plan_json:
        try:
            plan = json.loads(session.final_plan_json)
        except json.JSONDecodeError:
            plan = {"error": "Lỗi định dạng JSON trong kế hoạch đã lưu."}

    
    return jsonify({
        "conversation_id": session.id,
        "plan": plan,
        "plan_type": plan_type, 
        "chat_history": chat_history,
        "status": session.status if session.status else ("An toàn" if session.initial_detection == "Khỏe mạnh" else "Chờ xử lý")
    })
    
@user_bp.route('/knowledge-upload', methods=['POST'])
@jwt_required()
def upload_knowledge_file():
    file = request.files['file']
    store_type = request.form.get('store_type', 'general_qa')
    
    if not file.filename.endswith(('.txt', '.json')):
         return jsonify({"error": "Chỉ chấp nhận định dạng .txt, .json"}), 400

    try:
        file_content = file.read().decode('utf-8')
        
        result = current_app.vector_store.ingest_user_file_content(
             user_id=get_jwt_identity(),
             file_content=file_content,
             filename=file.filename,
             store_name=store_type
        )
        
        if result.get('success'):
            return jsonify({"message": result['message'], "total_chunks": result.get('chunk_count')}), 200
        else:
            return jsonify({"error": result.get('error', "Lỗi xử lý file")}), 500
            
    except Exception as e:
        current_app.logger.error(f"Lỗi xử lý tải file: {e}")
        return jsonify({"error": "Lỗi máy chủ khi xử lý file."}), 500