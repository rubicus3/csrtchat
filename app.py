from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from sqlalchemy import desc, func

import main_routes
import auth_routes

from config import Config
from models import db, User, Conversation, Message, Participant

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)

db.init_app(app)
migrate = Migrate(app, db)


login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "Пожалуйста, войдите для доступа к чату."


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_routes.auth)
app.register_blueprint(main_routes.main)


# --- HTTP ---

@app.route('/')
@login_required
def index():
    user_conversations = (
        db.session.query(Conversation)
        .join(Participant)
        .filter(Participant.user_id == current_user.user_id)
        .order_by(desc(Conversation.updated_at))
        .all()
    )

    return render_template('chat.html',
                           user=current_user,
                           conversations=user_conversations)


# --- WEBSOCKET ---

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        current_user.is_online = True
        db.session.commit()
        print(f"User {current_user.username} connected")
    else:
        return False


@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        current_user.is_online = False
        db.session.commit()
        print(f"User {current_user.username} disconnected")


@socketio.on('join')
def on_join(data):
    room = data['conversation_id']

    is_participant = Participant.query.filter_by(
        user_id=current_user.user_id,
        conversation_id=room
    ).first()

    if is_participant:
        join_room(room)
        print(f"User {current_user.username} joined room {room}")
    else:
        print(f"Access denied for user {current_user.username} to room {room}")


@socketio.on('leave')
def on_leave(data):
    room = data['conversation_id']
    leave_room(room)


@socketio.on('send_message')
def handle_message(data):
    conversation_id = data['conversation_id']
    content = data['message']

    is_participant = Participant.query.filter_by(
        user_id=current_user.user_id,
        conversation_id=conversation_id
    ).first()

    if not is_participant:
        return

    new_message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.user_id,
        content=content
    )
    db.session.add(new_message)

    conversation = Conversation.query.get(conversation_id)
    conversation.updated_at = func.now()
    db.session.commit()

    payload = {
        'message_id': new_message.message_id,
        'conversation_id': conversation_id,
        'sender_id': current_user.user_id,
        'sender_name': current_user.username,
        'content': new_message.content,
        'created_at': new_message.created_at.strftime('%H:%M')
    }

    emit('new_message', payload, room=conversation_id)


@socketio.on('delete_message')
@login_required
def handle_delete_message(data):
    message_id = data.get('message_id')
    conversation_id = data.get('conversation_id')

    message = db.session.get(Message, message_id)

    if not message:
        return

    if message.sender_id != current_user.user_id:
        print(f"Пользователь {current_user.username} попытался удалить чужое сообщение!")
        return

    db.session.delete(message)
    db.session.commit()

    emit('message_deleted', {
        'message_id': message_id,
        'conversation_id': conversation_id
    }, room=conversation_id)


@socketio.on('edit_message')
@login_required
def handle_edit_message(data):
    message_id = data.get('message_id')
    conversation_id = data.get('conversation_id')
    new_content = data.get('new_content')

    if not new_content or not new_content.strip():
        return

    message = db.session.get(Message, message_id)

    if not message:
        return
    if message.sender_id != current_user.user_id:
        return

    message.content = new_content
    message.is_edited = True
    db.session.commit()

    emit('message_updated', {
        'message_id': message_id,
        'conversation_id': conversation_id,
        'content': new_content,
        'is_edited': True
    }, room=conversation_id)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
