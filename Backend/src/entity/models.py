from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, date

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(10), nullable=False, default='farmer') 

    farms = db.relationship('Farm', back_populates='owner', lazy='dynamic', cascade='all, delete-orphan')

    settings = db.relationship('UserSettings', back_populates='user', uselist=False, cascade='all, delete-orphan')

    def __init__(self, username, password, full_name=None, role='farmer'):
        self.username = username
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        self.full_name = full_name
        self.role = role

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'User: {self.username} ({self.role})'
    
class UserSettings(db.Model):
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True)
    notification_enabled = db.Column(db.Boolean, nullable=False, default=True)
    notification_interval_hours = db.Column(db.Integer, nullable=False, default=4) 
    last_checked_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    user = db.relationship('User', back_populates='settings')

    def __repr__(self):
        return f'<UserSettings for User {self.user_id}>'
    
class Farm(db.Model):
    __tablename__ = 'farms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="Ruộng lúa")
    province = db.Column(db.String(50), nullable=False)
    area_ha = db.Column(db.Float, nullable=False)
    planting_date = db.Column(db.Date, nullable=True, default=date.today)
    soil_ph = db.Column(db.Float, nullable=True)
    soil_type = db.Column(db.String(50), nullable=True, default='chưa rõ') 
    rice_variety = db.Column(db.String(50), nullable=False, default='ST25') 

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    owner = db.relationship('User', back_populates='farms')

    analysis_sessions = db.relationship('AnalysisSession', back_populates='farm', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'Farm: {self.name}'
    
class AnalysisSession(db.Model):
    __tablename__ = 'analysis_sessions'

    id = db.Column(db.String(36), primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image_path = db.Column(db.String(255), nullable=True)
    initial_detection = db.Column(db.String(100), nullable=True)
    final_plan_json = db.Column(db.Text, nullable=True) 
    status = db.Column(db.String(20), nullable=False, default='pending') 

    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id'), nullable=False)

    farm = db.relationship('Farm', back_populates='analysis_sessions')

    messages = db.relationship('Message', back_populates='session', lazy='dynamic', cascade='all, delete-orphan') 

    def __repr__(self):
        return f'AnalysisSession {self.id}'
    
class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(10), nullable=False) 
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    session_id = db.Column(db.String(36), db.ForeignKey('analysis_sessions.id'), nullable=False)

    session = db.relationship('AnalysisSession', back_populates='messages')

    def __repr__(self):
        return f'Message from {self.sender}'