from database import db
from datetime import datetime
import enum

class ConversationStatus(enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

class User(db.Model):
    """Telegram users who interact with the bot"""
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    language_code = db.Column(db.String(10), default='fa')  # Persian by default
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_interaction = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    interactions = db.relationship('UserInteraction', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.telegram_id}>'

class Conversation(db.Model):
    """Customer conversations with the bot"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Enum(ConversationStatus), default=ConversationStatus.ACTIVE)
    subject = db.Column(db.String(200))  # Auto-generated conversation topic
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    escalated_at = db.Column(db.DateTime)  # When transferred to human support
    satisfaction_rating = db.Column(db.Integer)  # 1-5 stars
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy='dynamic')
    
    def __repr__(self):
        return f'<Conversation {self.id}>'

class Message(db.Model):
    """Individual messages in conversations"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    telegram_message_id = db.Column(db.Integer)
    content = db.Column(db.Text, nullable=False)
    is_from_user = db.Column(db.Boolean, default=True)  # True if from user, False if from bot
    is_ai_response = db.Column(db.Boolean, default=False)  # True if AI generated response
    ai_confidence = db.Column(db.Float)  # AI confidence score 0-1
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id}>'

class UserInteraction(db.Model):
    """Track user interactions with bot features"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interaction_type = db.Column(db.String(50), nullable=False)  # 'product_view', 'category_browse', 'order_track', etc.
    data = db.Column(db.JSON)  # Store interaction-specific data
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserInteraction {self.id}: {self.interaction_type}>'

class ProductView(db.Model):
    """Track product views through the bot"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)  # WooCommerce product ID
    product_name = db.Column(db.String(200))
    category_id = db.Column(db.Integer)
    category_name = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProductView {self.product_id} by {self.user_id}>'

class OrderTracking(db.Model):
    """Track order tracking requests"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_number = db.Column(db.String(50), nullable=False)
    woocommerce_order_id = db.Column(db.Integer)
    status_checked = db.Column(db.String(50))  # Last known order status
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OrderTracking {self.order_number}>'

class BotAnalytics(db.Model):
    """Daily analytics data"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    total_messages = db.Column(db.Integer, default=0)
    unique_users = db.Column(db.Integer, default=0)
    new_users = db.Column(db.Integer, default=0)
    ai_responses = db.Column(db.Integer, default=0)
    escalated_conversations = db.Column(db.Integer, default=0)
    product_views = db.Column(db.Integer, default=0)
    order_tracking_requests = db.Column(db.Integer, default=0)
    average_response_time = db.Column(db.Float)  # in seconds
    
    def __repr__(self):
        return f'<BotAnalytics {self.date}>'
