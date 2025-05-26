import os
import logging
from aiogram.fsm.storage.memory import MemoryStorage
from quart import Quart, request, current_app, jsonify
import datetime
from asyncio import to_thread

from werkzeug.middleware.proxy_fix import ProxyFix
from database import db
import threading
from quart_migrate import Migrate
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from aiogram.types import Update


TOKEN = os.getenv("BOT_TOKEN") or "7540724852:AAG-TfeGVGmssW4K3MLKkyiwwOyyqlsCGPI"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# TOKEN = "7540724852:AAG-TfeGVGmssW4K3MLKkyiwwOyyqlsCGPI"

# create the app
app = Quart(__name__)
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
async def dashboard():
    """Main dashboard page"""
    return await render_template('dashboard.html')

@app.route('/analytics')
async def analytics_page():
    """Analytics page"""
    return await render_template('analytics.html')

@app.route('/settings')
async def settings_page():
    """Settings page"""
    return await render_template('settings.html')

@app.route('/reports')
async def reports_page():
    """Reports page"""
    return await render_template('reports.html')

@app.route('/bot-config')
async def bot_config_page():
    """Bot configuration page"""
    return await render_template('bot_config.html')

@app.route('/ai-config')
async def ai_config_page():
    """AI configuration page"""
    return await render_template('ai_config.html')

@app.route('/woocommerce-config')
async def woocommerce_config_page():
    """WooCommerce configuration page"""
    return await render_template('woocommerce_config.html')

@app.route('/database')
async def database_page():
    """Database management page"""
    return await render_template('database.html')


@app.route('/api/overview')
async def api_overview():
    """API endpoint for dashboard overview data"""
    try:
        if not analytics_service:
            return jsonify({'error': 'Analytics service not initialized'}), 500

        loop = asyncio.get_running_loop()
        stats = await loop.run_in_executor(None, analytics_service.get_overview_stats)

        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f"Error in api_overview: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/popular-products')
async def api_popular_products():
    """API endpoint for popular products"""
    try:
        if not analytics_service:
            return jsonify({'error': 'Analytics service not initialized'}), 500

        loop = asyncio.get_running_loop()
        products = await loop.run_in_executor(None, analytics_service.get_popular_products, 5)

        return jsonify(products)
    except Exception as e:
        current_app.logger.error(f"Error in api_popular_products: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations')
async def api_conversations():
    """API endpoint for recent conversations"""
    try:
        if not analytics_service:
            return jsonify({'error': 'Analytics service not initialized'}), 500

        loop = asyncio.get_running_loop()
        conversations = await loop.run_in_executor(None, analytics_service.get_recent_conversations, 10)

        return jsonify(conversations)
    except Exception as e:
        current_app.logger.error(f"Error in api_conversations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/status')
async def api_bot_status():
    """API endpoint for bot status"""
    try:
        # نمونه: محاسبه uptime اگر bot_start_time داشته باشید
        if bot_instance and hasattr(bot_instance, "start_time"):
            uptime = datetime.datetime.utcnow() - bot_instance.start_time
            uptime_str = str(uptime).split('.')[0]  # حذف microseconds
        else:
            uptime_str = "unknown"

        # تعداد پیام‌ها مثلاً اگر جایی شمارنده داشته باشید:
        messages_processed = getattr(bot_instance, "message_count", 0)

        status = {
            'running': bot_instance is not None,
            'uptime': uptime_str,
            'messages_processed': messages_processed
        }
        return jsonify(status)
    except Exception as e:
        current_app.logger.error(f"Error in api_bot_status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/users')
async def api_analytics_users():
    """API endpoint for user analytics"""
    try:
        if not analytics_service:
            return jsonify({'error': 'Analytics service not initialized'}), 500

        # اگر متد sync هست، در async باید در executor اجرا بشه
        from asyncio import to_thread
        analytics = await to_thread(analytics_service.get_user_analytics)
        
        return jsonify(analytics)
    except Exception as e:
        logging.error(f"Error in api_analytics_users: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/status')
async def database_status():
    """Get database status and statistics"""
    try:
        if analytics_service is None:
            init_services()

        # تعریف تابع سینکرون برای اجرا در ترد جداگانه
        def fetch_database_info():
            tables_info = []
            try:
                with db.engine.connect() as conn:
                    user_count = conn.execute(db.text("SELECT COUNT(*) FROM user")).scalar()
                    tables_info.append({"name": "Users", "count": user_count})

                    conv_count = conn.execute(db.text("SELECT COUNT(*) FROM conversation")).scalar()
                    tables_info.append({"name": "Conversations", "count": conv_count})

                    msg_count = conn.execute(db.text("SELECT COUNT(*) FROM message")).scalar()
                    tables_info.append({"name": "Messages", "count": msg_count})

                    pv_count = conn.execute(db.text("SELECT COUNT(*) FROM product_view")).scalar()
                    tables_info.append({"name": "Product Views", "count": pv_count})

                    ot_count = conn.execute(db.text("SELECT COUNT(*) FROM order_tracking")).scalar()
                    tables_info.append({"name": "Order Tracking", "count": ot_count})
            except Exception as e:
                logging.warning(f"Could not get table counts: {e}")
                tables_info = [{"name": "Error", "count": "N/A"}]
            return tables_info

        # اجرای تابع در ترد جداگانه
        tables_info = await to_thread(fetch_database_info)

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


@app.post(f"/{TOKEN}")
async def webhook_handler():
    try:
        data = await request.get_json()
        update = Update.model_validate(data)
        await dp._process_update(update)
    except Exception as e:
        logging.exception("Webhook error")
    return "ok"

# تنظیم Webhook در on_startup
@app.before_serving
async def on_startup():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook set: {webhook_url}")

# حذف Webhook در shutdown
@app.after_serving
async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()

if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))


async def init_services():
    """Initialize services after app context is available"""
    global analytics_service, bot_instance

    import models
    # این تابع sync هست ولی چون فقط یک بار اجرا می‌شه، مشکلی نیست
    db.create_all()

    # Initialize analytics service
    from analytics import AnalyticsService
    analytics_service = AnalyticsService(db)

    return analytics_service


@app.route('/api/analytics/overview')
async def analytics_overview():
    """Get analytics overview data"""
    try:
        global analytics_service
        if analytics_service is None:
            await init_services()

        overview = analytics_service.get_overview()
        return jsonify(overview)
    except Exception as e:
        logging.error(f"Error getting analytics overview: {e}")
        return jsonify({"error": "Failed to fetch analytics data"}), 500

@app.route('/api/analytics/conversations')
async def analytics_conversations():
    """Get conversation analytics"""
    try:
        global analytics_service
        if analytics_service is None:
            await init_services()

        days = request.args.get('days', 7, type=int)
        conversations = analytics_service.get_conversation_stats(days)
        return jsonify(conversations)
    except Exception as e:
        logging.error(f"Error getting conversation analytics: {e}")
        return jsonify({"error": "Failed to fetch conversation data"}), 500


@app.route('/api/analytics/popular-products')
async def popular_products():
    """Get popular products data"""
    try:
        global analytics_service
        if analytics_service is None:
            await init_services()

        products = analytics_service.get_popular_products()
        return jsonify(products)
    except Exception as e:
        logging.error(f"Error getting popular products: {e}")
        return jsonify({"error": "Failed to fetch product data"}), 500


async def start_bot():
    """Start the Telegram bot"""
    global bot_instance, analytics_service

    try:
        if analytics_service is None:
            await init_services()

        from bot import TelegramBot
        bot_instance = TelegramBot(db, analytics_service)
        # اگر bot_instance نیاز به start() دارد و آن تابع async است:
        # await bot_instance.start()
    except Exception as e:
        logging.error(f"Failed to start Telegram bot: {e}")


# راه‌اندازی اولیه async (مثلاً در startup)
@app.before_serving
async def startup():
    """Initialize services and bot before serving"""
    await init_services()
    await start_bot()

from quart import Quart
import asyncio

async def create_app():
    """Quart Application Factory"""
    app = Quart(__name__)
    app.secret_key = os.getenv("SESSION_SECRET", "dev-secret-key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///telegram_bot.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    db.init_app(app)
    migrate.init_app(app, db)

    from analytics import AnalyticsService
    from bot import TelegramBot

    # --- Async lifecycle hooks ---
    @app.before_serving
    async def startup():
        global analytics_service, bot_instance
        async with app.app_context():
            db.create_all()
            analytics_service = AnalyticsService(db)
            bot_instance = TelegramBot(db, analytics_service)
            asyncio.create_task(bot_instance.start())  # async start method
            await bot_instance.set_webhook()  # optional webhook

    @app.after_serving
    async def shutdown():
        if bot_instance:
            await bot_instance.application.shutdown()
            await bot_instance.application.session.close()

    return app


if __name__ == '__main__':
    # Create the application
    app = create_app()


    # bot = TelegramBot(db=db_instance, analytics_service=analytics_instance)
    # asyncio.run(bot.application.run_polling())

    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)

