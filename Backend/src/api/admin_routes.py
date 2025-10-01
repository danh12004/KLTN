from flask import Blueprint, jsonify, request
from src.repository.admin_user_repository import AdminUserRepository
from src.repository.admin_farm_repository import AdminFarmRepository
from src.repository.admin_analysis_repository import AdminAnalysisRepository
from src.entity.models import db, User, Farm, AnalysisSession

admin_bp = Blueprint("admin", __name__)

user_repo = AdminUserRepository()
farm_repo = AdminFarmRepository()
session_repo = AdminAnalysisRepository()

@admin_bp.route("/stats", methods=["GET"])
def get_stats():
    return jsonify({
        "totalUsers": User.query.count(),
        "totalFarms": Farm.query.count(),
        "totalSessions": AnalysisSession.query.count()
    })

@admin_bp.route("/users", methods=["GET"])
def get_users():
    users = user_repo.get_all_users()
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role
    } for u in users])

@admin_bp.route("/users", methods=["POST"])
def create_user():
    data = request.json
    try:
        new_user = user_repo.create_user(
            username=data["username"],
            password=data["password"],
            full_name=data.get("full_name"),
            role=data.get("role", "farmer")
        )
        db.session.commit()
        return jsonify({
            "id": new_user.id,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "role": new_user.role
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = user_repo.get_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    data = request.json
    user.full_name = data.get("full_name", user.full_name)
    user.role = data.get("role", user.role)
    if 'password' in data and data['password']:
        user.set_password(data['password'])

    user_repo.commit() 
    return jsonify({"success": True, "message": "User updated successfully"})


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    success = user_repo.delete_user(user_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "User not found"}), 404

@admin_bp.route("/farms", methods=["GET"])
def get_farms():
    farms = farm_repo.get_all_farms()
    return jsonify([{
        "id": f.id,
        "name": f.name,
        "province": f.province,
        "area_ha": f.area_ha,
        "rice_variety": f.rice_variety,
        "owner": {
            "id": f.owner.id,
            "username": f.owner.username
        } if f.owner else None
    } for f in farms])

@admin_bp.route("/farms/<int:farm_id>", methods=["DELETE"])
def delete_farm(farm_id):
    success = farm_repo.delete_farm(farm_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Farm not found"}), 404
    
@admin_bp.route("/farms/<int:farm_id>", methods=["PUT"])
def update_farm(farm_id):
    farm = farm_repo.get_by_id(farm_id)
    if not farm:
        return jsonify({"error": "Farm not found"}), 404
    
    data = request.json
    farm.name = data.get("name", farm.name)
    farm.province = data.get("province", farm.province)
    farm.area_ha = data.get("area_ha", farm.area_ha)
    farm.rice_variety = data.get("rice_variety", farm.rice_variety)

    farm_repo.commit()
    return jsonify({"success": True, "message": "Farm updated successfully"})

@admin_bp.route("/sessions", methods=["GET"])
def get_sessions():
    sessions = session_repo.get_all_sessions()
    return jsonify([{
        "id": s.id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "initial_detection": s.initial_detection,
        "status": s.status,
        "farm": {
            "id": s.farm.id,
            "name": s.farm.name
        } if s.farm else None
    } for s in sessions])

@admin_bp.route("/sessions/<string:session_id>", methods=["DELETE"])
def delete_session(session_id):
    success = session_repo.delete_session(session_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Session not found"}), 404
