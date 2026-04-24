from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from database import db, Room, Player, generate_room_code
from config import Config
import uuid
from functools import wraps

# إنشاء تطبيق Flask
app = Flask(__name__)
app.config.from_object(Config)

# تهيئة قاعدة البيانات
db.init_app(app)

# تهيئة SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================== Helper Functions ====================

def get_current_player():
    """الحصول على بيانات اللاعب الحالي"""
    session_id = session.get('session_id')
    if not session_id:
        return None
    return Player.query.filter_by(session_id=session_id).first()

def init_session():
    """تهيئة معرف الجلسة الفريد للاعب"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session.permanent = True

def require_player(f):
    """ديكوريتر للتحقق من وجود لاعب متصل"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        player = get_current_player()
        if not player:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== Database Commands ====================

@app.shell_context_processor
def make_shell_context():
    """توفير نماذج قاعدة البيانات في shell"""
    return {'db': db, 'Room': Room, 'Player': Player}

# ==================== Routes ====================

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    init_session()
    return render_template('index.html')

@app.route('/create-room', methods=['GET', 'POST'])
def create_room():
    """إنشاء غرفة جديدة"""
    init_session()
    
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '').strip()
        
        if not username or len(username) < 2:
            return jsonify({'success': False, 'error': 'اسم اللاعب قصير جداً'}), 400
        
        if len(username) > 50:
            return jsonify({'success': False, 'error': 'اسم اللاعب طويل جداً'}), 400
        
        session_id = session.get('session_id')
        
        # التحقق من عدم وجود لاعب بنفس الجلسة
        existing_player = Player.query.filter_by(session_id=session_id).first()
        if existing_player:
            db.session.delete(existing_player)
            db.session.commit()
        
        try:
            # توليد كود الغرفة
            room_code = generate_room_code()
            while Room.query.filter_by(code=room_code).first():
                room_code = generate_room_code()
            
            # إنشاء لاعب جديد (Host)
            player = Player(
                username=username,
                session_id=session_id,
                is_host=True
            )
            db.session.add(player)
            db.session.flush()
            
            # إنشاء الغرفة
            room = Room(
                code=room_code,
                host_id=player.id
            )
            db.session.add(room)
            db.session.commit()
            
            player.room_id = room.id
            db.session.commit()
            
            return jsonify({
                'success': True,
                'room_code': room_code,
                'room_id': room.id
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return render_template('create_room.html')

@app.route('/join-room', methods=['GET', 'POST'])
def join_room():
    """صفحة الانضمام إلى غرفة"""
    init_session()
    
    if request.method == 'POST':
        data = request.get_json()
        room_code = data.get('room_code', '').strip().upper()
        username = data.get('username', '').strip()
        
        if not username or len(username) < 2:
            return jsonify({'success': False, 'error': 'اسم اللاعب قصير جداً'}), 400
        
        if not room_code or len(room_code) != 6:
            return jsonify({'success': False, 'error': 'كود الغرفة غير صحيح'}), 400
        
        session_id = session.get('session_id')
        room = Room.query.filter_by(code=room_code).first()
        
        if not room:
            return jsonify({'success': False, 'error': 'الغرفة غير موجودة'}), 404
        
        if room.status != 'waiting':
            return jsonify({'success': False, 'error': 'الغرفة قد بدأت اللعب بالفعل'}), 400
        
        if len(room.players) >= 10:
            return jsonify({'success': False, 'error': 'الغرفة ممتلئة'}), 400
        
        # التحقق من عدم وجود لاعب بنفس الجلسة
        existing_player = Player.query.filter_by(session_id=session_id).first()
        if existing_player:
            db.session.delete(existing_player)
            db.session.commit()
        
        try:
            # إنشاء لاعب جديد
            player = Player(
                username=username,
                session_id=session_id,
                room_id=room.id,
                is_host=False
            )
            db.session.add(player)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'room_code': room.code,
                'room_id': room.id
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return render_template('join_room.html')

@app.route('/room/<room_code>')
@require_player
def waiting_room(room_code):
    """غرفة الانتظار"""
    player = get_current_player()
    room = Room.query.filter_by(code=room_code).first()
    
    if not room or player.room_id != room.id:
        return redirect(url_for('index'))
    
    return render_template('waiting_room.html', room=room, player=player)

@app.route('/api/room/<int:room_id>')
def get_room_data(room_id):
    """الحصول على بيانات الغرفة"""
    player = get_current_player()
    room = Room.query.get(room_id)
    
    if not room or not player or player.room_id != room.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'code': room.code,
        'status': room.status,
        'host_id': room.host_id,
        'players': [p.to_dict() for p in room.players]
    })

# ==================== SocketIO Events ====================

@socketio.on('connect')
def handle_connect():
    """معالجة اتصال اللاعب"""
    print(f"اللاعب متصل: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """معالجة قطع اتصال اللاعب"""
    print(f"اللاعب غير متصل: {request.sid}")

@socketio.on('join_waiting_room')
def handle_join_waiting_room(data):
    """انضمام اللاعب إلى غرفة الانتظار"""
    player = get_current_player()
    room_code = data.get('room_code')
    
    if not player:
        emit('error', {'message': 'غير مصرح'})
        return
    
    room = Room.query.filter_by(code=room_code).first()
    if not room or player.room_id != room.id:
        emit('error', {'message': 'الغرفة غير موجودة'})
        return
    
    # الانضمام إلى socket room
    join_room(f'room_{room.id}')
    
    # إرسال قائمة اللاعبين الحالية
    players_data = [p.to_dict() for p in room.players]
    emit('players_updated', {
        'players': players_data,
        'player_count': len(players_data)
    }, room=f'room_{room.id}')

@socketio.on('player_joined')
def handle_player_joined(data):
    """إخطار بانضمام لاعب جديد"""
    player = get_current_player()
    room = player.room if player else None
    
    if not room:
        return
    
    players_data = [p.to_dict() for p in room.players]
    emit('players_updated', {
        'players': players_data,
        'player_count': len(players_data)
    }, room=f'room_{room.id}')

@socketio.on('start_game')
def handle_start_game(data):
    """بدء اللعبة من قبل Host"""
    player = get_current_player()
    room = player.room if player else None
    
    if not room or not player.is_host:
        emit('error', {'message': 'غير مصرح'})
        return
    
    if len(room.players) < 4:  # الحد الأدنى من اللاعبين
        emit('error', {'message': 'عدد اللاعبين غير كافي'})
        return
    
    # تحديث حالة الغرفة
    room.status = 'playing'
    db.session.commit()
    
    emit('game_started', {
        'message': 'اللعبة بدأت!'
    }, room=f'room_{room.id}')

# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    """معالج الصفحة غير الموجودة"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """معالج خطأ الخادم"""
    db.session.rollback()
    return render_template('500.html'), 500

# ==================== CLI Commands ====================

@app.cli.command()
def init_db():
    """تهيئة قاعدة البيانات"""
    db.create_all()
    print('تم تهيئة قاعدة البيانات بنجاح')

@app.cli.command()
def reset_db():
    """إعادة تعيين قاعدة البيانات"""
    if input('هل أنت متأكد؟ (yes/no): ').lower() == 'yes':
        db.drop_all()
        db.create_all()
        print('تم إعادة تعيين قاعدة البيانات بنجاح')

# ==================== Main ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    socketio.run(app, debug=True, host='127.0.0.1', port=5000)
