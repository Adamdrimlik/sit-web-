"""
Database Models for Mafia Online Game
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from app import db
import string
import random
import json

class GameSettings(db.Model):
    """Game settings for each room"""
    __tablename__ = 'game_settings'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)

    # Player counts
    min_players = db.Column(db.Integer, default=6)
    max_players = db.Column(db.Integer, default=15)

    # Role counts
    mafia_count = db.Column(db.Integer, default=2)
    doctor_count = db.Column(db.Integer, default=1)
    police_count = db.Column(db.Integer, default=1)
    sheikh_count = db.Column(db.Integer, default=1)
    sniper_count = db.Column(db.Integer, default=0)

    # Time settings (in seconds)
    day_time = db.Column(db.Integer, default=300)  # 5 minutes
    night_time = db.Column(db.Integer, default=120)  # 2 minutes
    voting_time = db.Column(db.Integer, default=60)  # 1 minute
    discussion_time = db.Column(db.Integer, default=180)  # 3 minutes

    # Game options
    random_roles = db.Column(db.Boolean, default=True)
    private_roles = db.Column(db.Boolean, default=True)
    auto_start = db.Column(db.Boolean, default=False)

    # Voice settings
    voice_enabled = db.Column(db.Boolean, default=True)
    mafia_voice_room = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Room(db.Model):
    """Game room model"""
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)
    host_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)

    # Room status
    status = db.Column(db.String(20), default='waiting')  # waiting, starting, playing, finished
    game_phase = db.Column(db.String(20), default='lobby')  # lobby, night, day, voting, discussion

    # Game state
    current_round = db.Column(db.Integer, default=0)
    night_number = db.Column(db.Integer, default=0)
    day_number = db.Column(db.Integer, default=0)

    # Game results
    winner_team = db.Column(db.String(20))  # mafia, citizens, none

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    # Relationships
    players = db.relationship('Player', backref='room', lazy=True, cascade='all, delete-orphan')
    host = db.relationship('Player', foreign_keys=[host_id], backref='hosted_rooms')
    settings = db.relationship('GameSettings', backref='room', uselist=False, cascade='all, delete-orphan')
    game_logs = db.relationship('GameLog', backref='room', lazy=True, cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.code:
            self.code = self.generate_room_code()
        if not self.settings:
            self.settings = GameSettings()

    @staticmethod
    def generate_room_code(length=8):
        """Generate unique room code"""
        characters = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(characters) for _ in range(length))
            if not Room.query.filter_by(code=code).first():
                return code

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'status': self.status,
            'game_phase': self.game_phase,
            'player_count': len(self.players),
            'max_players': self.settings.max_players if self.settings else 15,
            'host_username': self.host.username if self.host else None,
            'created_at': self.created_at.isoformat(),
            'current_round': self.current_round,
        }

    def get_alive_players(self):
        """Get list of alive players"""
        return [p for p in self.players if p.is_alive]

    def get_mafia_players(self):
        """Get list of mafia players"""
        return [p for p in self.players if p.role and 'mafia' in p.role.lower()]

    def get_citizen_players(self):
        """Get list of citizen players"""
        return [p for p in self.players if p.role and 'mafia' not in p.role.lower()]

class Player(db.Model):
    """Player model"""
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)

    # Player status
    is_host = db.Column(db.Boolean, default=False)
    is_connected = db.Column(db.Boolean, default=True)
    is_alive = db.Column(db.Boolean, default=True)
    is_ready = db.Column(db.Boolean, default=False)

    # Game data
    role = db.Column(db.String(30))  # mafia_boss, mafia_member, doctor, police, sheikh, sniper, citizen
    role_description = db.Column(db.Text)
    has_voted = db.Column(db.Boolean, default=False)
    vote_target = db.Column(db.Integer, db.ForeignKey('players.id'))

    # Voice settings
    voice_enabled = db.Column(db.Boolean, default=True)
    microphone_enabled = db.Column(db.Boolean, default=True)

    # Statistics
    games_played = db.Column(db.Integer, default=0)
    games_won = db.Column(db.Integer, default=0)
    mafia_wins = db.Column(db.Integer, default=0)
    citizen_wins = db.Column(db.Integer, default=0)

    # Timestamps
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    voted_by = db.relationship('Player', foreign_keys=[vote_target], backref='votes_received')

    def __repr__(self):
        return f'<Player {self.username}>'

    def to_dict(self, include_role=False, include_private=False):
        data = {
            'id': self.id,
            'username': self.username,
            'is_host': self.is_host,
            'is_connected': self.is_connected,
            'is_alive': self.is_alive,
            'is_ready': self.is_ready,
            'joined_at': self.joined_at.isoformat(),
            'last_seen': self.last_seen.isoformat(),
        }

        if include_role:
            data.update({
                'role': self.role,
                'role_description': self.role_description,
            })

        if include_private:
            data.update({
                'session_id': self.session_id,
                'voice_enabled': self.voice_enabled,
                'microphone_enabled': self.microphone_enabled,
                'games_played': self.games_played,
                'games_won': self.games_won,
            })

        return data

    def get_team(self):
        """Get player's team"""
        if not self.role:
            return None
        if 'mafia' in self.role.lower():
            return 'mafia'
        return 'citizens'

class GameLog(db.Model):
    """Game events log"""
    __tablename__ = 'game_logs'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)

    # Event data
    event_type = db.Column(db.String(50), nullable=False)  # player_joined, player_left, vote_cast, player_killed, etc.
    event_data = db.Column(db.Text)  # JSON data
    round_number = db.Column(db.Integer, default=0)
    phase = db.Column(db.String(20))  # night, day, voting, discussion

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, event_type, event_data=None, **kwargs):
        super().__init__(**kwargs)
        self.event_type = event_type
        if event_data:
            self.event_data = json.dumps(event_data) if isinstance(event_data, dict) else event_data

    def get_event_data(self):
        """Get parsed event data"""
        if self.event_data:
            try:
                return json.loads(self.event_data)
            except:
                return self.event_data
        return {}

class Vote(db.Model):
    """Voting system"""
    __tablename__ = 'votes'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    round_number = db.Column(db.Integer, default=0)
    phase = db.Column(db.String(20), default='day')  # day, night

    # Relationships
    voter = db.relationship('Player', foreign_keys=[voter_id], backref='votes_cast')
    target = db.relationship('Player', foreign_keys=[target_id], backref='votes_received_list')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Utility functions
def get_player_by_session(session_id):
    """Get player by session ID"""
    return Player.query.filter_by(session_id=session_id).first()

def get_room_by_code(code):
    """Get room by code"""
    return Room.query.filter_by(code=code.upper()).first()

def create_room_with_settings(host_player, room_name=None):
    """Create room with default settings"""
    room = Room(host_id=host_player.id, name=room_name)
    db.session.add(room)
    db.session.flush()  # Get room ID

    settings = GameSettings(room_id=room.id)
    db.session.add(settings)
    db.session.commit()

    return room
