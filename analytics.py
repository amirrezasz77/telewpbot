import logging
from datetime import datetime, timedelta, date
from sqlalchemy import func, desc
from models import (
    User, Conversation, Message, UserInteraction, 
    ProductView, OrderTracking, BotAnalytics
)

class AnalyticsService:
    """Service for generating bot analytics and insights"""
    
    def __init__(self, db):
        self.db = db
        logging.info("Analytics service initialized")
    
    def get_overview(self):
        """Get overview analytics"""
        try:
            with self.db.session() as session:
                # Total users
                total_users = session.query(User).count()
                
                # Active users (last 7 days)
                week_ago = datetime.utcnow() - timedelta(days=7)
                active_users = session.query(User).filter(
                    User.last_interaction >= week_ago
                ).count()
                
                # Total conversations
                total_conversations = session.query(Conversation).count()
                
                # Active conversations
                active_conversations = session.query(Conversation).filter(
                    Conversation.status == 'active'
                ).count()
                
                # Escalated conversations (last 30 days)
                month_ago = datetime.utcnow() - timedelta(days=30)
                escalated_conversations = session.query(Conversation).filter(
                    Conversation.escalated_at >= month_ago
                ).count()
                
                # Total messages today
                today = date.today()
                messages_today = session.query(Message).filter(
                    func.date(Message.timestamp) == today
                ).count()
                
                # AI vs Human responses
                ai_messages = session.query(Message).filter(
                    Message.is_ai_response == True
                ).count()
                
                total_bot_messages = session.query(Message).filter(
                    Message.is_from_user == False
                ).count()
                
                # Product views (last 7 days)
                product_views_week = session.query(ProductView).filter(
                    ProductView.timestamp >= week_ago
                ).count()
                
                # Order tracking requests (last 7 days)
                order_tracking_week = session.query(OrderTracking).filter(
                    OrderTracking.timestamp >= week_ago
                ).count()
                
                # Average satisfaction rating
                avg_rating = session.query(func.avg(Conversation.satisfaction_rating)).filter(
                    Conversation.satisfaction_rating.isnot(None)
                ).scalar() or 0
                
                return {
                    'total_users': total_users,
                    'active_users': active_users,
                    'total_conversations': total_conversations,
                    'active_conversations': active_conversations,
                    'escalated_conversations': escalated_conversations,
                    'messages_today': messages_today,
                    'ai_response_rate': round((ai_messages / max(total_bot_messages, 1)) * 100, 2),
                    'product_views_week': product_views_week,
                    'order_tracking_week': order_tracking_week,
                    'avg_satisfaction_rating': round(avg_rating, 2)
                }
                
        except Exception as e:
            logging.error(f"Error getting overview analytics: {e}")
            return {}
    
    def get_conversation_stats(self, days: int = 7):
        """Get conversation statistics for the last N days"""
        try:
            with self.db.session() as session:
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # Daily conversation counts
                daily_stats = session.query(
                    func.date(Conversation.started_at).label('date'),
                    func.count(Conversation.id).label('conversations')
                ).filter(
                    Conversation.started_at >= start_date
                ).group_by(
                    func.date(Conversation.started_at)
                ).order_by('date').all()
                
                # Daily message counts
                daily_messages = session.query(
                    func.date(Message.timestamp).label('date'),
                    func.count(Message.id).label('messages')
                ).filter(
                    Message.timestamp >= start_date
                ).group_by(
                    func.date(Message.timestamp)
                ).order_by('date').all()
                
                # Convert to dictionaries for easier processing
                conversations_dict = {str(stat.date): stat.conversations for stat in daily_stats}
                messages_dict = {str(stat.date): stat.messages for stat in daily_messages}
                
                # Generate complete date range
                result = []
                current_date = start_date.date()
                end_date = datetime.utcnow().date()
                
                while current_date <= end_date:
                    date_str = str(current_date)
                    result.append({
                        'date': date_str,
                        'conversations': conversations_dict.get(date_str, 0),
                        'messages': messages_dict.get(date_str, 0)
                    })
                    current_date += timedelta(days=1)
                
                return result
                
        except Exception as e:
            logging.error(f"Error getting conversation stats: {e}")
            return []
    
    def get_popular_products(self, limit: int = 10):
        """Get most popular products based on views"""
        try:
            with self.db.session() as session:
                # Last 30 days
                month_ago = datetime.utcnow() - timedelta(days=30)
                
                popular_products = session.query(
                    ProductView.product_id,
                    ProductView.product_name,
                    ProductView.category_name,
                    func.count(ProductView.id).label('view_count')
                ).filter(
                    ProductView.timestamp >= month_ago
                ).group_by(
                    ProductView.product_id,
                    ProductView.product_name,
                    ProductView.category_name
                ).order_by(
                    desc('view_count')
                ).limit(limit).all()
                
                return [{
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'category_name': product.category_name or 'Unknown',
                    'view_count': product.view_count
                } for product in popular_products]
                
        except Exception as e:
            logging.error(f"Error getting popular products: {e}")
            return []
    
    def get_user_activity(self, days: int = 30):
        """Get user activity statistics"""
        try:
            with self.db.session() as session:
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # New users per day
                new_users = session.query(
                    func.date(User.created_at).label('date'),
                    func.count(User.id).label('new_users')
                ).filter(
                    User.created_at >= start_date
                ).group_by(
                    func.date(User.created_at)
                ).order_by('date').all()
                
                # Active users per day
                active_users = session.query(
                    func.date(User.last_interaction).label('date'),
                    func.count(func.distinct(User.id)).label('active_users')
                ).filter(
                    User.last_interaction >= start_date
                ).group_by(
                    func.date(User.last_interaction)
                ).order_by('date').all()
                
                return {
                    'new_users': [{'date': str(stat.date), 'count': stat.new_users} for stat in new_users],
                    'active_users': [{'date': str(stat.date), 'count': stat.active_users} for stat in active_users]
                }
                
        except Exception as e:
            logging.error(f"Error getting user activity: {e}")
            return {'new_users': [], 'active_users': []}
    
    def get_interaction_breakdown(self):
        """Get breakdown of interaction types"""
        try:
            with self.db.session() as session:
                # Last 30 days
                month_ago = datetime.utcnow() - timedelta(days=30)
                
                interactions = session.query(
                    UserInteraction.interaction_type,
                    func.count(UserInteraction.id).label('count')
                ).filter(
                    UserInteraction.timestamp >= month_ago
                ).group_by(
                    UserInteraction.interaction_type
                ).order_by(
                    desc('count')
                ).all()
                
                return [{
                    'interaction_type': interaction.interaction_type,
                    'count': interaction.count
                } for interaction in interactions]
                
        except Exception as e:
            logging.error(f"Error getting interaction breakdown: {e}")
            return []
    
    def get_ai_performance(self):
        """Get AI performance metrics"""
        try:
            with self.db.session() as session:
                # Last 30 days
                month_ago = datetime.utcnow() - timedelta(days=30)
                
                # Average AI confidence
                avg_confidence = session.query(
                    func.avg(Message.ai_confidence)
                ).filter(
                    Message.is_ai_response == True,
                    Message.timestamp >= month_ago,
                    Message.ai_confidence.isnot(None)
                ).scalar() or 0
                
                # Confidence distribution
                confidence_ranges = [
                    ('0.0-0.2', 0.0, 0.2),
                    ('0.2-0.4', 0.2, 0.4),
                    ('0.4-0.6', 0.4, 0.6),
                    ('0.6-0.8', 0.6, 0.8),
                    ('0.8-1.0', 0.8, 1.0)
                ]
                
                confidence_distribution = []
                for range_label, min_conf, max_conf in confidence_ranges:
                    count = session.query(Message).filter(
                        Message.is_ai_response == True,
                        Message.timestamp >= month_ago,
                        Message.ai_confidence >= min_conf,
                        Message.ai_confidence < max_conf if max_conf < 1.0 else Message.ai_confidence <= max_conf
                    ).count()
                    
                    confidence_distribution.append({
                        'range': range_label,
                        'count': count
                    })
                
                # Escalation rate
                total_conversations = session.query(Conversation).filter(
                    Conversation.started_at >= month_ago
                ).count()
                
                escalated_conversations = session.query(Conversation).filter(
                    Conversation.started_at >= month_ago,
                    Conversation.escalated_at.isnot(None)
                ).count()
                
                escalation_rate = (escalated_conversations / max(total_conversations, 1)) * 100
                
                return {
                    'average_confidence': round(avg_confidence, 3),
                    'confidence_distribution': confidence_distribution,
                    'escalation_rate': round(escalation_rate, 2),
                    'total_ai_responses': session.query(Message).filter(
                        Message.is_ai_response == True,
                        Message.timestamp >= month_ago
                    ).count()
                }
                
        except Exception as e:
            logging.error(f"Error getting AI performance: {e}")
            return {}
    
    def get_satisfaction_trends(self, days: int = 30):
        """Get satisfaction rating trends"""
        try:
            with self.db.session() as session:
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # Daily average ratings
                daily_ratings = session.query(
                    func.date(Conversation.ended_at).label('date'),
                    func.avg(Conversation.satisfaction_rating).label('avg_rating'),
                    func.count(Conversation.satisfaction_rating).label('rating_count')
                ).filter(
                    Conversation.ended_at >= start_date,
                    Conversation.satisfaction_rating.isnot(None)
                ).group_by(
                    func.date(Conversation.ended_at)
                ).order_by('date').all()
                
                # Rating distribution
                rating_distribution = session.query(
                    Conversation.satisfaction_rating.label('rating'),
                    func.count(Conversation.id).label('count')
                ).filter(
                    Conversation.ended_at >= start_date,
                    Conversation.satisfaction_rating.isnot(None)
                ).group_by(
                    Conversation.satisfaction_rating
                ).order_by('rating').all()
                
                return {
                    'daily_ratings': [{
                        'date': str(rating.date),
                        'avg_rating': round(rating.avg_rating, 2),
                        'count': rating.rating_count
                    } for rating in daily_ratings],
                    'rating_distribution': [{
                        'rating': rating.rating,
                        'count': rating.count
                    } for rating in rating_distribution]
                }
                
        except Exception as e:
            logging.error(f"Error getting satisfaction trends: {e}")
            return {'daily_ratings': [], 'rating_distribution': []}
    
    def update_daily_analytics(self):
        """Update daily analytics data"""
        try:
            with self.db.session() as session:
                today = date.today()
                
                # Check if today's analytics already exist
                existing = session.query(BotAnalytics).filter_by(date=today).first()
                
                if existing:
                    analytics = existing
                else:
                    analytics = BotAnalytics(date=today)
                    session.add(analytics)
                
                # Calculate today's stats
                analytics.total_messages = session.query(Message).filter(
                    func.date(Message.timestamp) == today
                ).count()
                
                analytics.unique_users = session.query(func.count(func.distinct(User.telegram_id))).filter(
                    func.date(User.last_interaction) == today
                ).scalar() or 0
                
                analytics.new_users = session.query(User).filter(
                    func.date(User.created_at) == today
                ).count()
                
                analytics.ai_responses = session.query(Message).filter(
                    func.date(Message.timestamp) == today,
                    Message.is_ai_response == True
                ).count()
                
                analytics.escalated_conversations = session.query(Conversation).filter(
                    func.date(Conversation.escalated_at) == today
                ).count()
                
                analytics.product_views = session.query(ProductView).filter(
                    func.date(ProductView.timestamp) == today
                ).count()
                
                analytics.order_tracking_requests = session.query(OrderTracking).filter(
                    func.date(OrderTracking.timestamp) == today
                ).count()
                
                session.commit()
                logging.info(f"Daily analytics updated for {today}")
                
        except Exception as e:
            logging.error(f"Error updating daily analytics: {e}")
    
    def get_total_users(self):
        """Get total number of users"""
        try:
            with self.db.session() as session:
                return session.query(User).count()
        except Exception as e:
            logging.error(f"Error getting total users: {e}")
            return 0
    
    def get_active_conversations(self):
        """Get number of active conversations"""
        try:
            with self.db.session() as session:
                return session.query(Conversation).filter(
                    Conversation.status == 'active'
                ).count()
        except Exception as e:
            logging.error(f"Error getting active conversations: {e}")
            return 0
