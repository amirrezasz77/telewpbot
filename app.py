import os
import logging
from flask import Flask, render_template, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix
from database import db
import threading
from flask_migrate import Migrate
import asyncio

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# configure the database - PostgreSQL
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    database_url = "sqlite:///telegram_bot.db"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# init extensions
db.init_app(app)
migrate = Migrate(app, db)

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

@app.route('/woocommerce-config')
def woocommerce_config_page():
    """WooCommerce configuration page"""
    return render_template('woocommerce_config.html')

@app.route('/database')
def database_page():
    """Database management page"""
    return render_template('database.html')

# API Endpoints for Dashboard
@app.route('/api/overview')
def api_overview():
    """API endpoint for dashboard overview data"""
    try:
        if not analytics_service:
            return jsonify({'error': 'Analytics service not initialized'}), 500

        # Get overview statistics
        stats = analytics_service.get_overview_stats()
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Error in api_overview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/popular-products')
def api_popular_products():
    """API endpoint for popular products"""
    try:
        if not analytics_service:
            return jsonify({'error': 'Analytics service not initialized'}), 500

        products = analytics_service.get_popular_products(limit=5)
        return jsonify(products)
    except Exception as e:
        logging.error(f"Error in api_popular_products: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations')
def api_conversations():
    """API endpoint for recent conversations"""
    try:
        if not analytics_service:
            return jsonify({'error': 'Analytics service not initialized'}), 500

        conversations = analytics_service.get_recent_conversations(limit=10)
        return jsonify(conversations)
    except Exception as e:
        logging.error(f"Error in api_conversations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/status')
def api_bot_status():
    """API endpoint for bot status"""
    try:
        status = {
            'running': bot_instance is not None,
            'uptime': '00:00:00',  # You can implement proper uptime tracking
            'messages_processed': 0  # You can implement message counting
        }
        return jsonify(status)
    except Exception as e:
        logging.error(f"Error in api_bot_status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/users')
def api_analytics_users():
    """API endpoint for user analytics"""
    try:
        if not analytics_service:
            return jsonify({'error': 'Analytics service not initialized'}), 500

        analytics = analytics_service.get_user_analytics()
        return jsonify(analytics)
    except Exception as e:
        logging.error(f"Error in api_analytics_users: {e}")
        return jsonify({'error': str(e)}), 500

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

    # Start the bot automatically - temporarily disabled due to import issues
    # bot_thread = threading.Thread(target=start_bot, daemon=True)
    # bot_thread.start()

def create_app():
    """Application factory"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    with app.app_context():
        # Create database tables
        db.create_all()

        # Initialize analytics service
        global analytics_service
        if not analytics_service:
            from analytics import AnalyticsService
            analytics_service = AnalyticsService(db)
            logging.info("Analytics service initialized")

        # Initialize and start bot in a separate thread
        global bot_instance
        if not bot_instance:
            from bot import TelegramBot
            try:
                bot_instance = TelegramBot(db, analytics_service)
                bot_thread = threading.Thread(target=bot_instance.start, daemon=True)
                bot_thread.start()
                logging.info("Telegram bot started in separate thread")
            except Exception as e:
                logging.error(f"Failed to start Telegram bot: {e}")

    return app

if __name__ == '__main__':
    # Create the application
    app = create_app()


    bot = TelegramBot(db=db_instance, analytics_service=analytics_instance)
    asyncio.run(bot.application.run_polling())

    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)

