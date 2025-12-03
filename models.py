from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import enum
from sqlalchemy import MetaData
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import ENUM

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)


class ConversationType(enum.Enum):
    private = "private"
    group = "group"


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255))
    status_message = db.Column(db.String(150))
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime(timezone=True), server_default=func.now())
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    participants = db.relationship('Participant', back_populates='user', cascade='all, delete-orphan')
    messages = db.relationship('Message', back_populates='sender')

    def get_id(self):
        return str(self.user_id)

    def __repr__(self):
        return f'<User {self.username}>'


class Conversation(db.Model):
    __tablename__ = 'conversations'

    conversation_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(ENUM(ConversationType, name='conversation_type', create_type=False), nullable=False,
                     default=ConversationType.private)
    name = db.Column(db.String(100))
    avatar_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    participants = db.relationship('Participant', back_populates='conversation', cascade='all, delete-orphan')
    messages = db.relationship('Message', back_populates='conversation', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Conversation {self.conversation_id} ({self.type.value})>'


class Participant(db.Model):
    __tablename__ = 'participants'

    participant_id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.conversation_id', ondelete='CASCADE'),
                                nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    joined_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    is_admin = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint('conversation_id', 'user_id', name='uq_participants_conversation_user'),)

    conversation = db.relationship('Conversation', back_populates='participants')
    user = db.relationship('User', back_populates='participants')


class Message(db.Model):
    __tablename__ = 'messages'

    message_id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.conversation_id', ondelete='CASCADE'),
                                nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_edited = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    conversation = db.relationship('Conversation', back_populates='messages')
    sender = db.relationship('User', back_populates='messages')

    def to_dict(self):
        return {
            'message_id': self.message_id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
