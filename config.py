import os

class Config:
    """Configuration class for the application"""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # WooCommerce Configuration
    WOOCOMMERCE_URL = os.environ.get('WOOCOMMERCE_URL')  # e.g., 'https://yourstore.com'
    WOOCOMMERCE_CONSUMER_KEY = os.environ.get('WOOCOMMERCE_CONSUMER_KEY')
    WOOCOMMERCE_CONSUMER_SECRET = os.environ.get('WOOCOMMERCE_CONSUMER_SECRET')
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///telegram_bot.db')
    
    # Application Configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # Bot Configuration
    BOT_NAME = os.environ.get('BOT_NAME', 'فروشگاه آنلاین')  # Persian: Online Store
    SUPPORT_CONTACT = os.environ.get('SUPPORT_CONTACT', '@support')
    
    # AI Configuration
    AI_MODEL = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    AI_MAX_TOKENS = 1000
    AI_TEMPERATURE = 0.7
    
    # Local AI Configuration
    USE_LOCAL_AI = os.environ.get('USE_LOCAL_AI', 'False').lower() == 'true'
    OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
    LOCAL_AI_MODEL = os.environ.get('LOCAL_AI_MODEL', 'llama3.2')
    
    # Languages
    DEFAULT_LANGUAGE = 'fa'  # Persian/Farsi
    SUPPORTED_LANGUAGES = ['fa', 'en']
    
    @staticmethod
    def validate():
        """Validate that required configuration is present"""
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'OPENAI_API_KEY',
            'WOOCOMMERCE_URL',
            'WOOCOMMERCE_CONSUMER_KEY',
            'WOOCOMMERCE_CONSUMER_SECRET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True

# Language templates for bot responses
MESSAGES = {
    'fa': {
        'welcome': '🔸سلام! به ربات فروشگاه خوش آمدید. چطور می‌تونم کمکتون کنم؟',
        'main_menu': '📋 منوی اصلی',
        'products': '🛍️ محصولات',
        'categories': '📂 دسته‌بندی‌ها',
        'order_tracking': '📦 پیگیری سفارش',
        'support': '💬 پشتیبانی',
        'back': '🔙 بازگشت',
        'error': '❌ خطایی رخ داده است. لطفاً دوباره تلاش کنید.',
        'order_number_prompt': 'لطفاً شماره سفارش خود را وارد کنید:',
        'escalating_to_human': '🔄 در حال انتقال به پشتیبان انسانی...',
        'human_support_message': 'سوال شما به تیم پشتیبانی ارسال شد. به زودی پاسخ دریافت خواهید کرد.',
        'typing': '⌨️ در حال تایپ...',
        'processing': '⏳ در حال پردازش...',
        'no_products': 'هیچ محصولی در این دسته‌بندی یافت نشد.',
        'view_product': '👁️ مشاهده محصول',
        'price': 'قیمت:',
        'in_stock': 'موجود',
        'out_of_stock': 'ناموجود',
        'order_found': '✅ سفارش یافت شد:',
        'order_not_found': '❌ سفارش با این شماره یافت نشد.',
        'rate_conversation': 'لطفاً کیفیت خدمات ما را از ۱ تا ۵ ستاره امتیاز دهید:'
    },
    'en': {
        'welcome': '🔸Hello! Welcome to our store bot. How can I help you?',
        'main_menu': '📋 Main Menu',
        'products': '🛍️ Products',
        'categories': '📂 Categories',
        'order_tracking': '📦 Order Tracking',
        'support': '💬 Support',
        'back': '🔙 Back',
        'error': '❌ An error occurred. Please try again.',
        'order_number_prompt': 'Please enter your order number:',
        'escalating_to_human': '🔄 Transferring to human support...',
        'human_support_message': 'Your question has been sent to our support team. You will receive a response soon.',
        'typing': '⌨️ Typing...',
        'processing': '⏳ Processing...',
        'no_products': 'No products found in this category.',
        'view_product': '👁️ View Product',
        'price': 'Price:',
        'in_stock': 'In Stock',
        'out_of_stock': 'Out of Stock',
        'order_found': '✅ Order found:',
        'order_not_found': '❌ Order with this number not found.',
        'rate_conversation': 'Please rate our service from 1 to 5 stars:'
    }
}
