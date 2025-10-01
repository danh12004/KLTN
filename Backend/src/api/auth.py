from flask import Blueprint, request, jsonify
from src.entity.models import db, User
from flask_jwt_extended import create_access_token
import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        additional_claims = {"role": user.role}
        expires = datetime.timedelta(days=7)
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims=additional_claims,
            expires_delta=expires
        )
        return jsonify(access_token=access_token)

    return jsonify({"error": "Sai username hoặc password"}), 401