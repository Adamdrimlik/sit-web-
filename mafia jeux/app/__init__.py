"""
Mafia Online - Professional Mafia Game
A complete online Mafia game with voice chat, roles, and real-time gameplay.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS
import os
from datetime import timedelta

# Initialize extensions
db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*")

def create_app(config_name='development'):
    """Application Factory Pattern"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    template_folder = os.path.join(base_dir, 'templates')
    static_folder = os.path.join(base_dir, 'static')

    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder,
        static_url_path='/static'
    )

    # Load configuration
    if config_name == 'production':
        app.config.from_object('app.config.ProductionConfig')
    elif config_name == 'testing':
        app.config.from_object('app.config.TestingConfig')
    else:
        app.config.from_object('app.config.DevelopmentConfig')

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    CORS(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.game import game_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(game_bp, url_prefix='/game')

    # Register Socket.IO events
    from app.socket_events import register_socket_events
    register_socket_events(socketio)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app

def create_database():
    """Create database tables"""
    from app import create_app
    app = create_app()
    with app.app_context():
        db.create_all()
        print("✅ Database created successfully!")

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
