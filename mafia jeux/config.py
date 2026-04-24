import os
from datetime import timedelta

class Config:
    """إعدادات التطبيق الأساسية"""
    
    # قاعدة البيانات
    SQLALCHEMY_DATABASE_URI = 'sqlite:///mafia_game.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # السرية
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # SocketIO
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_CORS_ALLOWED_ORIGINS = '*'
    
    # جلسة المستخدم
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # إعدادات اللعبة
    MIN_PLAYERS = 4
    MAX_PLAYERS = 10
    ROOM_CODE_LENGTH = 6
    WAITING_ROOM_TIMEOUT = 600  # 10 دقائق
