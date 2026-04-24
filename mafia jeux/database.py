from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import string
import random

db = SQLAlchemy()

def generate_room_code(length=6):
    """توليد كود عشوائي للغرفة"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

class Room(db.Model):
    """نموذج غرفة اللعبة"""
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False, index=True)
    host_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    status = db.Column(db.String(20), default='waiting')  # waiting, playing, finished
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    
    # العلاقات
    players = db.relationship('Player', backref='room', lazy=True, cascade='all, delete-orphan')
    host = db.relationship('Player', foreign_keys=[host_id], backref='hosted_rooms')
    
    def __repr__(self):
        return f'<Room {self.code}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'status': self.status,
            'player_count': len(self.players),
            'created_at': self.created_at.isoformat(),
        }

class Player(db.Model):
    """نموذج اللاعب"""
    __tablename__ = 'players'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    is_host = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20))  # mafia, doctor, police, citizen
    is_alive = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Player {self.username}>'
    
    def to_dict(self, include_role=False):
        data = {
            'id': self.id,
            'username': self.username,
            'is_host': self.is_host,
            'is_alive': self.is_alive,
            'joined_at': self.joined_at.isoformat(),
        }
        if include_role:
            data['role'] = self.role
        return data
