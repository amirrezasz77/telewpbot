import os
import logging
from flask import Flask, render_template, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix
from database import db
import threading

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///telegram_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# initialize the app with the extension
db.init_app(app)

# Global variables
analytics_service = None
bot_instance = None

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/analytics')
def analytics_page():
    """Analytics page"""
    return render_template('analytics.html')

def init_services():
    """Initialize services after app context is available"""
    global analytics_service, bot_instance
    
    # Import models here so their tables get created
    import models
    db.create_all()
    
    # Initialize analytics service
    from analytics import AnalyticsService
    analytics_service = AnalyticsService(db)
    
    return analytics_service

@app.route('/api/analytics/overview')
def analytics_overview():
    """Get analytics overview data"""
    try:
        if analytics_service is None:
            init_services()
        overview = analytics_service.get_overview()
        return jsonify(overview)
    except Exception as e:
        logging.error(f"Error getting analytics overview: {e}")
        return jsonify({"error": "Failed to fetch analytics data"}), 500

@app.route('/api/analytics/conversations')
def analytics_conversations():
    """Get conversation analytics"""
    try:
        if analytics_service is None:
            init_services()
        days = request.args.get('days', 7, type=int)
        conversations = analytics_service.get_conversation_stats(days)
        return jsonify(conversations)
    except Exception as e:
        logging.error(f"Error getting conversation analytics: {e}")
        return jsonify({"error": "Failed to fetch conversation data"}), 500

@app.route('/api/analytics/popular-products')
def popular_products():
    """Get popular products data"""
    try:
        if analytics_service is None:
            init_services()
        products = analytics_service.get_popular_products()
        return jsonify(products)
    except Exception as e:
        logging.error(f"Error getting popular products: {e}")
        return jsonify({"error": "Failed to fetch product data"}), 500

@app.route('/api/bot/status')
def bot_status():
    """Get bot status"""
    try:
        if analytics_service is None:
            init_services()
        # This would be updated by the bot when it's running
        return jsonify({
            "status": "online",
            "last_update": "2024-01-01T00:00:00Z",
            "total_users": analytics_service.get_total_users(),
            "active_conversations": analytics_service.get_active_conversations()
        })
    except Exception as e:
        logging.error(f"Error getting bot status: {e}")
        return jsonify({"error": "Failed to fetch bot status"}), 500

def start_bot():
    """Start the Telegram bot in a separate thread"""
    global bot_instance, analytics_service
    try:
        if analytics_service is None:
            with app.app_context():
                init_services()
        
        from bot import TelegramBot
        bot_instance = TelegramBot(db, analytics_service)
        bot_instance.start()
    except Exception as e:
        logging.error(f"Failed to start Telegram bot: {e}")

# Initialize services when the module is imported
with app.app_context():
    init_services()

if __name__ == '__main__':
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
