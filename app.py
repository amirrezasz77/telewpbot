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

# configure the database - PostgreSQL
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # Fallback to SQLite for development
    database_url = "sqlite:///telegram_bot.db"
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
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

@app.route('/settings')
def settings_page():
    """Settings page"""
    return render_template('settings.html')

@app.route('/reports')
def reports_page():
    """Reports page"""
    return render_template('reports.html')

@app.route('/bot-config')
def bot_config_page():
    """Bot configuration page"""
    return render_template('bot_config.html')

@app.route('/ai-config')
def ai_config_page():
    """AI configuration page"""
    return render_template('ai_config.html')

@app.route('/database')
def database_page():
    """Database management page"""
    return render_template('database.html')

@app.route('/api/database/status')
def database_status():
    """Get database status and statistics"""
    try:
        if analytics_service is None:
            init_services()
        
        # Get database info
        with db.engine.connect() as conn:
            # Get table counts
            tables_info = []
            try:
                # Users table
                user_count = conn.execute(db.text("SELECT COUNT(*) FROM user")).scalar()
                tables_info.append({"name": "Users", "count": user_count})
                
                # Conversations table
                conv_count = conn.execute(db.text("SELECT COUNT(*) FROM conversation")).scalar()
                tables_info.append({"name": "Conversations", "count": conv_count})
                
                # Messages table
                msg_count = conn.execute(db.text("SELECT COUNT(*) FROM message")).scalar()
                tables_info.append({"name": "Messages", "count": msg_count})
                
                # Product views table
                pv_count = conn.execute(db.text("SELECT COUNT(*) FROM product_view")).scalar()
                tables_info.append({"name": "Product Views", "count": pv_count})
                
                # Order tracking table
                ot_count = conn.execute(db.text("SELECT COUNT(*) FROM order_tracking")).scalar()
                tables_info.append({"name": "Order Tracking", "count": ot_count})
                
            except Exception as e:
                logging.warning(f"Could not get table counts: {e}")
                tables_info = [{"name": "Error", "count": "N/A"}]
        
        return jsonify({
            "status": "connected",
            "database_type": "PostgreSQL",
            "tables": tables_info,
            "connection_info": {
                "host": os.environ.get("PGHOST", "localhost"),
                "port": os.environ.get("PGPORT", "5432"),
                "database": os.environ.get("PGDATABASE", "")
            }
        })
        
    except Exception as e:
        logging.error(f"Database status error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

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
    
    # Start the bot automatically
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

if __name__ == '__main__':
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
