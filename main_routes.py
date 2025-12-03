from flask import render_template, request, jsonify, Blueprint
from flask_login import login_required, current_user
from sqlalchemy import desc, and_

from models import db, Conversation, Participant, Message, User, ConversationType


main = Blueprint('main', __name__)


# --- HTTP ---

@main.route('/')
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


# --- API ---

@main.route('/api/messages/<int:convo_id>', methods=['GET'])
@login_required
def get_messages(convo_id):
    is_participant = Participant.query.filter_by(
        user_id=current_user.user_id,
        conversation_id=convo_id
    ).first()

    if not is_participant:
        return jsonify({'error': 'Доступ запрещен или чат не существует'}), 403

    messages = Message.query.filter_by(conversation_id=convo_id) \
        .order_by(desc(Message.created_at)) \
        .limit(50) \
        .all()
    messages.reverse()

    messages_data = []
    for msg in messages:
        sender_name = msg.sender.username if msg.sender else 'Удаленный пользователь'
        messages_data.append({
            'message_id': msg.message_id,
            'sender_id': msg.sender_id,
            'sender_name': sender_name,
            'content': msg.content,
            'is_edited': msg.is_edited,
            'created_at': msg.created_at.strftime('%H:%M')
        })

    return jsonify(messages_data)


@main.route('/api/users/search', methods=['GET'])
@login_required
def search_users():
    query = request.args.get('q', '').strip()

    if len(query) < 2:
        return jsonify([])

    users = User.query.filter(
        and_(
            User.username.ilike(f'%{query}%'),
            User.user_id != current_user.user_id
        )
    ).limit(10).all()

    results = [{'id': u.user_id, 'username': u.username, 'email': u.email} for u in users]
    return jsonify(results)


@main.route('/api/conversation/create', methods=['POST'])
@login_required
def create_conversation():
    data = request.get_json()
    participant_ids = data.get('participant_ids', [])

    if not participant_ids:
        return jsonify({'error': 'Необходимо указать участников'}), 400

    if current_user.user_id not in participant_ids:
        participant_ids.append(current_user.user_id)

    is_private = len(participant_ids) == 2
    chat_type = ConversationType.private if is_private else ConversationType.group

    new_convo = Conversation(
        type=chat_type,
        name=data.get('name') if not is_private else None
    )
    db.session.add(new_convo)
    db.session.commit()

    participants = []
    for user_id in participant_ids:
        is_admin = (not is_private) and (user_id == current_user.user_id)
        participants.append(Participant(
            conversation_id=new_convo.conversation_id,
            user_id=user_id,
            is_admin=is_admin
        ))

    db.session.bulk_save_objects(participants)
    db.session.commit()

    return jsonify({
        'message': 'Чат успешно создан',
        'conversation_id': new_convo.conversation_id,
        'type': chat_type.value
    }), 201
