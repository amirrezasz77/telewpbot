from database import db
from datetime import datetime
import enum

class ConversationStatus(enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    language_code = Column(String(10), default='fa')
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user")
    interactions = relationship("UserInteraction", back_populates="user")
    product_views = relationship("ProductView", back_populates="user")
    order_trackings = relationship("OrderTracking", back_populates="user")

    def __repr__(self):
        return f"<User {self.telegram_id}>"

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE)
    subject = Column(String(200))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    escalated_at = Column(DateTime)
    satisfaction_rating = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

    def __repr__(self):
        return f"<Conversation {self.id}>"







class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    telegram_message_id = Column(Integer)
    content = Column(String)
    is_from_user = Column(Boolean, default=True)
    is_ai_response = Column(Boolean, default=False)
    ai_confidence = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id}>"

class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    interaction_type = Column(String(50), nullable=False)
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interactions")

    def __repr__(self):
        return f"<UserInteraction {self.id}>"

class ProductView(Base):
    __tablename__ = "product_views"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(200))
    category_id = Column(Integer)
    category_name = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="product_views")

    def __repr__(self):
        return f"<ProductView {self.product_id} by {self.user_id}>"

class OrderTracking(Base):
    __tablename__ = "order_trackings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_number = Column(String(50), nullable=False)
    woocommerce_order_id = Column(Integer)
    status_checked = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="order_trackings")

    def __repr__(self):
        return f"<OrderTracking {self.order_number}>"

class BotAnalytics(Base):
    __tablename__ = "bot_analytics"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True)
    total_messages = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    new_users = Column(Integer, default=0)
    ai_responses = Column(Integer, default=0)
    escalated_conversations = Column(Integer, default=0)
    product_views = Column(Integer, default=0)
    order_tracking_requests = Column(Integer, default=0)
    average_response_time = Column(Float)


    def __repr__(self):
        return f"<BotAnalytics {self.date}>"
