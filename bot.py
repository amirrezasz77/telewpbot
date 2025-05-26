import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ChatAction
from datetime import datetime
import threading
import time

from config import Config, MESSAGES
from models import User, Conversation, Message, UserInteraction, ProductView, OrderTracking
from ai_service import AIService
from woocommerce_api import WooCommerceAPI

class TelegramBot:
    """Main Telegram Bot class"""
    
    def __init__(self, db, analytics_service):
        self.token = Config.TELEGRAM_BOT_TOKEN
        if not self.token:
            raise ValueError("Telegram bot token is not configured")
        
        self.db = db
        self.analytics_service = analytics_service
        self.ai_service = AIService()
        self.woo_api = WooCommerceAPI()
        
        # Initialize bot application
        self.application = Application.builder().token(self.token).build()
        
        # User sessions to track conversation state
        self.user_sessions = {}
        
        self._setup_handlers()
        logging.info("Telegram bot initialized")
    
    def _setup_handlers(self):
        """Setup command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("menu", self.main_menu_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("support", self.support_command))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = await self._get_or_create_user(update.effective_user)
        language = user.language_code or 'fa'
        
        # Send welcome message
        welcome_message = MESSAGES[language]['welcome']
        await update.message.reply_text(welcome_message)
        
        # Show main menu
        await self._show_main_menu(update, language)
        
        # Track interaction
        await self._track_interaction(user.id, 'bot_start')
    
    async def main_menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command"""
        user = await self._get_or_create_user(update.effective_user)
        language = user.language_code or 'fa'
        await self._show_main_menu(update, language)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user = await self._get_or_create_user(update.effective_user)
        language = user.language_code or 'fa'
        
        if language == 'fa':
            help_text = """
🤖 راهنمای استفاده از ربات

📋 دستورات اصلی:
/start - شروع مجدد ربات
/menu - نمایش منوی اصلی
/help - نمایش این راهنما
/support - ارتباط با پشتیبانی

🛍️ امکانات:
• مشاهده محصولات و دسته‌بندی‌ها
• پیگیری سفارشات
• چت با هوش مصنوعی
• ارتباط با پشتیبانی انسانی

💬 فقط پیام خود را بنویسید و من پاسخ خواهم داد!
"""
        else:
            help_text = """
🤖 Bot Usage Guide

📋 Main Commands:
/start - Restart the bot
/menu - Show main menu
/help - Show this guide
/support - Contact support

🛍️ Features:
• View products and categories
• Track orders
• Chat with AI
• Contact human support

💬 Just type your message and I'll respond!
"""
        
        await update.message.reply_text(help_text)
    
    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /support command"""
        user = await self._get_or_create_user(update.effective_user)
        language = user.language_code or 'fa'
        
        await self._escalate_to_human(update, user, language)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user = await self._get_or_create_user(update.effective_user)
        language = user.language_code or 'fa'
        message_text = update.message.text
        
        # Get or create conversation
        conversation = await self._get_or_create_conversation(user)
        
        # Save user message
        await self._save_message(conversation.id, message_text, is_from_user=True, 
                                telegram_message_id=update.message.message_id)
        
        # Check if user is providing order number
        session = self.user_sessions.get(user.telegram_id, {})
        if session.get('waiting_for_order_number'):
            await self._handle_order_tracking(update, user, message_text, language)
            return
        
        # Show typing action
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # Analyze intent first
        intent_analysis = self.ai_service.analyze_intent(message_text, language)
        
        # Handle specific intents
        if intent_analysis['intent'] == 'order_tracking':
            entities = intent_analysis.get('entities', {})
            order_number = entities.get('order_number')
            if order_number:
                await self._handle_order_tracking(update, user, order_number, language)
                return
            else:
                await self._prompt_for_order_number(update, user, language)
                return
        
        elif intent_analysis['intent'] == 'category_browse':
            await self._show_categories(update, language)
            return
        
        elif intent_analysis['intent'] == 'product_inquiry':
            # If looking for specific product, try to help
            await self._handle_product_inquiry(update, user, message_text, language)
            return
        
        # Generate AI response
        conversation_context = await self._get_conversation_context(conversation.id)
        ai_response = self.ai_service.generate_response(
            message_text, conversation_context, language
        )
        
        # Check if should escalate to human
        if ai_response['should_escalate'] or ai_response['confidence'] < 0.3:
            await self._escalate_to_human(update, user, language)
            return
        
        # Send AI response
        response_text = ai_response['response']
        await update.message.reply_text(response_text)
        
        # Save bot response
        await self._save_message(conversation.id, response_text, is_from_user=False, 
                                is_ai_response=True, ai_confidence=ai_response['confidence'])
        
        # Track interaction
        await self._track_interaction(user.id, 'ai_conversation', {
            'intent': intent_analysis['intent'],
            'confidence': ai_response['confidence']
        })
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user = await self._get_or_create_user(update.effective_user)
        language = user.language_code or 'fa'
        
        data = query.data
        
        if data == 'show_categories':
            await self._show_categories_inline(query, language)
        
        elif data == 'order_tracking':
            await self._prompt_for_order_number_inline(query, user, language)
        
        elif data == 'contact_support':
            await self._escalate_to_human_inline(query, user, language)
        
        elif data == 'main_menu':
            await self._show_main_menu_inline(query, language)
        
        elif data.startswith('category_'):
            category_id = int(data.replace('category_', ''))
            await self._show_category_products(query, user, category_id, language)
        
        elif data.startswith('product_'):
            product_id = int(data.replace('product_', ''))
            await self._show_product_details(query, user, product_id, language)
        
        elif data.startswith('rate_'):
            rating = int(data.replace('rate_', ''))
            await self._handle_rating(query, user, rating, language)
    
    async def _show_main_menu(self, update: Update, language: str):
        """Show main menu keyboard"""
        keyboard = [
            [MESSAGES[language]['categories'], MESSAGES[language]['order_tracking']],
            [MESSAGES[language]['support']]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            MESSAGES[language]['main_menu'],
            reply_markup=reply_markup
        )
    
    async def _show_main_menu_inline(self, query, language: str):
        """Show main menu with inline keyboard"""
        keyboard = [
            [InlineKeyboardButton(MESSAGES[language]['categories'], callback_data='show_categories')],
            [InlineKeyboardButton(MESSAGES[language]['order_tracking'], callback_data='order_tracking')],
            [InlineKeyboardButton(MESSAGES[language]['support'], callback_data='contact_support')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            MESSAGES[language]['main_menu'],
            reply_markup=reply_markup
        )
    
    async def _show_categories(self, update: Update, language: str):
        """Show product categories"""
        try:
            categories = self.woo_api.get_categories()
            
            if not categories:
                await update.message.reply_text(MESSAGES[language]['error'])
                return
            
            keyboard = []
            for category in categories[:15]:  # Show max 15 categories
                keyboard.append([InlineKeyboardButton(
                    f"📂 {category['name']} ({category['count']})",
                    callback_data=f"category_{category['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton(MESSAGES[language]['back'], callback_data='main_menu')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                MESSAGES[language]['categories'],
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logging.error(f"Error showing categories: {e}")
            await update.message.reply_text(MESSAGES[language]['error'])
    
    async def _show_categories_inline(self, query, language: str):
        """Show categories with inline keyboard"""
        try:
            categories = self.woo_api.get_categories()
            
            if not categories:
                await query.edit_message_text(MESSAGES[language]['error'])
                return
            
            keyboard = []
            for category in categories[:15]:
                keyboard.append([InlineKeyboardButton(
                    f"📂 {category['name']} ({category['count']})",
                    callback_data=f"category_{category['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton(MESSAGES[language]['back'], callback_data='main_menu')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                MESSAGES[language]['categories'],
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logging.error(f"Error showing categories inline: {e}")
            await query.edit_message_text(MESSAGES[language]['error'])
    
    async def _show_category_products(self, query, user: User, category_id: int, language: str):
        """Show products in a category"""
        try:
            products = self.woo_api.get_products(category_id=category_id, per_page=10)
            
            if not products:
                await query.edit_message_text(MESSAGES[language]['no_products'])
                return
            
            keyboard = []
            for product in products:
                keyboard.append([InlineKeyboardButton(
                    f"🛍️ {product['name'][:30]}..." if len(product['name']) > 30 else f"🛍️ {product['name']}",
                    callback_data=f"product_{product['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton(MESSAGES[language]['back'], callback_data='show_categories')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"🛍️ محصولات" if language == 'fa' else "🛍️ Products",
                reply_markup=reply_markup
            )
            
            # Track category view
            await self._track_interaction(user.id, 'category_browse', {'category_id': category_id})
            
        except Exception as e:
            logging.error(f"Error showing category products: {e}")
            await query.edit_message_text(MESSAGES[language]['error'])
    
    async def _show_product_details(self, query, user: User, product_id: int, language: str):
        """Show detailed product information"""
        try:
            product = self.woo_api.get_product(product_id)
            
            if not product:
                await query.edit_message_text(MESSAGES[language]['error'])
                return
            
            # Format product message
            product_message = self.woo_api.format_product_message(product, language)
            
            keyboard = [
                [InlineKeyboardButton(MESSAGES[language]['back'], callback_data='show_categories')]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                product_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Track product view
            await self._track_product_view(user.id, product)
            
        except Exception as e:
            logging.error(f"Error showing product details: {e}")
            await query.edit_message_text(MESSAGES[language]['error'])
    
    async def _prompt_for_order_number(self, update: Update, user: User, language: str):
        """Prompt user to enter order number"""
        self.user_sessions[user.telegram_id] = {'waiting_for_order_number': True}
        
        await update.message.reply_text(MESSAGES[language]['order_number_prompt'])
    
    async def _prompt_for_order_number_inline(self, query, user: User, language: str):
        """Prompt user to enter order number (inline)"""
        self.user_sessions[user.telegram_id] = {'waiting_for_order_number': True}
        
        await query.edit_message_text(MESSAGES[language]['order_number_prompt'])
    
    async def _handle_order_tracking(self, update: Update, user: User, order_number: str, language: str):
        """Handle order tracking request"""
        try:
            # Clear session
            if user.telegram_id in self.user_sessions:
                del self.user_sessions[user.telegram_id]
            
            # Search for order
            order = self.woo_api.search_order_by_number(order_number.strip())
            
            if order:
                order_message = self.woo_api.format_order_message(order, language)
                await update.message.reply_text(order_message, parse_mode='Markdown')
                
                # Track order tracking
                await self._track_order_tracking(user.id, order_number, order.get('id'))
            else:
                await update.message.reply_text(MESSAGES[language]['order_not_found'])
            
        except Exception as e:
            logging.error(f"Error tracking order: {e}")
            await update.message.reply_text(MESSAGES[language]['error'])
    
    async def _handle_product_inquiry(self, update: Update, user: User, message_text: str, language: str):
        """Handle product-related inquiries"""
        try:
            # Search for products based on the message
            products = self.woo_api.search_products(message_text, per_page=5)
            
            if products:
                keyboard = []
                for product in products:
                    keyboard.append([InlineKeyboardButton(
                        f"🛍️ {product['name'][:30]}..." if len(product['name']) > 30 else f"🛍️ {product['name']}",
                        callback_data=f"product_{product['id']}"
                    )])
                
                keyboard.append([InlineKeyboardButton(MESSAGES[language]['back'], callback_data='main_menu')])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                search_message = f"🔍 نتایج جستجو برای '{message_text}':" if language == 'fa' else f"🔍 Search results for '{message_text}':"
                
                await update.message.reply_text(
                    search_message,
                    reply_markup=reply_markup
                )
            else:
                # No products found, use AI to respond
                conversation = await self._get_or_create_conversation(user)
                conversation_context = await self._get_conversation_context(conversation.id)
                ai_response = self.ai_service.generate_response(
                    message_text, conversation_context, language
                )
                
                await update.message.reply_text(ai_response['response'])
                
                # Save AI response
                await self._save_message(conversation.id, ai_response['response'], 
                                        is_from_user=False, is_ai_response=True, 
                                        ai_confidence=ai_response['confidence'])
            
        except Exception as e:
            logging.error(f"Error handling product inquiry: {e}")
            await update.message.reply_text(MESSAGES[language]['error'])
    
    async def _escalate_to_human(self, update: Update, user: User, language: str):
        """Escalate conversation to human support"""
        # Mark current conversation as escalated
        conversation = await self._get_or_create_conversation(user)
        
        with self.db.session() as session:
            conv = session.get(Conversation, conversation.id)
            if conv:
                conv.status = 'escalated'
                conv.escalated_at = datetime.utcnow()
                session.commit()
        
        escalation_message = MESSAGES[language]['escalating_to_human']
        support_message = MESSAGES[language]['human_support_message']
        
        await update.message.reply_text(escalation_message)
        await update.message.reply_text(f"{support_message}\n\n{Config.SUPPORT_CONTACT}")
        
        # Track escalation
        await self._track_interaction(user.id, 'escalation')
        
        # Ask for rating
        await self._request_rating(update, user, language)
    
    async def _escalate_to_human_inline(self, query, user: User, language: str):
        """Escalate to human support (inline)"""
        conversation = await self._get_or_create_conversation(user)
        
        with self.db.session() as session:
            conv = session.get(Conversation, conversation.id)
            if conv:
                conv.status = 'escalated'
                conv.escalated_at = datetime.utcnow()
                session.commit()
        
        support_message = MESSAGES[language]['human_support_message']
        
        await query.edit_message_text(f"{support_message}\n\n{Config.SUPPORT_CONTACT}")
        
        # Track escalation
        await self._track_interaction(user.id, 'escalation')
    
    async def _request_rating(self, update: Update, user: User, language: str):
        """Request conversation rating from user"""
        keyboard = []
        stars = ['⭐', '⭐⭐', '⭐⭐⭐', '⭐⭐⭐⭐', '⭐⭐⭐⭐⭐']
        
        for i, star in enumerate(stars):
            keyboard.append([InlineKeyboardButton(star, callback_data=f"rate_{i+1}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            MESSAGES[language]['rate_conversation'],
            reply_markup=reply_markup
        )
    
    async def _handle_rating(self, query, user: User, rating: int, language: str):
        """Handle conversation rating"""
        # Save rating to current conversation
        conversation = await self._get_current_conversation(user)
        
        if conversation:
            with self.db.session() as session:
                conv = session.get(Conversation, conversation.id)
                if conv:
                    conv.satisfaction_rating = rating
                    conv.ended_at = datetime.utcnow()
                    conv.status = 'resolved'
                    session.commit()
        
        thank_you = "ممنون از امتیاز شما! 🙏" if language == 'fa' else "Thank you for your rating! 🙏"
        
        await query.edit_message_text(thank_you)
        
        # Track rating
        await self._track_interaction(user.id, 'rating', {'rating': rating})
    
    async def _get_or_create_user(self, telegram_user) -> User:
        """Get or create user from Telegram user object"""
        with self.db.session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_user.id).first()
            
            if not user:
                user = User(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                    language_code=telegram_user.language_code or 'fa'
                )
                session.add(user)
                session.commit()
                session.refresh(user)
            else:
                # Update last interaction
                user.last_interaction = datetime.utcnow()
                session.commit()
            
            return user
    
    async def _get_or_create_conversation(self, user: User) -> Conversation:
        """Get active conversation or create new one"""
        with self.db.session() as session:
            # Look for active conversation
            conversation = session.query(Conversation).filter_by(
                user_id=user.id,
                status='active'
            ).first()
            
            if not conversation:
                conversation = Conversation(
                    user_id=user.id,
                    status='active'
                )
                session.add(conversation)
                session.commit()
                session.refresh(conversation)
            
            return conversation
    
    async def _get_current_conversation(self, user: User) -> Conversation:
        """Get current active conversation"""
        with self.db.session() as session:
            return session.query(Conversation).filter_by(
                user_id=user.id,
                status='active'
            ).first()
    
    async def _save_message(self, conversation_id: int, content: str, is_from_user: bool = True, 
                           telegram_message_id: int = None, is_ai_response: bool = False, 
                           ai_confidence: float = None):
        """Save message to database"""
        with self.db.session() as session:
            message = Message(
                conversation_id=conversation_id,
                content=content,
                is_from_user=is_from_user,
                telegram_message_id=telegram_message_id,
                is_ai_response=is_ai_response,
                ai_confidence=ai_confidence
            )
            session.add(message)
            session.commit()
    
    async def _get_conversation_context(self, conversation_id: int) -> list:
        """Get conversation context for AI"""
        with self.db.session() as session:
            messages = session.query(Message).filter_by(
                conversation_id=conversation_id
            ).order_by(Message.timestamp.desc()).limit(10).all()
            
            return [{
                'content': msg.content,
                'is_from_user': msg.is_from_user,
                'timestamp': msg.timestamp.isoformat()
            } for msg in reversed(messages)]
    
    async def _track_interaction(self, user_id: int, interaction_type: str, data: dict = None):
        """Track user interaction"""
        with self.db.session() as session:
            interaction = UserInteraction(
                user_id=user_id,
                interaction_type=interaction_type,
                data=data or {}
            )
            session.add(interaction)
            session.commit()
    
    async def _track_product_view(self, user_id: int, product: dict):
        """Track product view"""
        with self.db.session() as session:
            product_view = ProductView(
                user_id=user_id,
                product_id=product['id'],
                product_name=product['name'],
                category_id=product.get('categories', [{}])[0].get('id') if product.get('categories') else None,
                category_name=product.get('categories', [{}])[0].get('name') if product.get('categories') else None
            )
            session.add(product_view)
            session.commit()
    
    async def _track_order_tracking(self, user_id: int, order_number: str, woocommerce_order_id: int = None):
        """Track order tracking request"""
        with self.db.session() as session:
            order_tracking = OrderTracking(
                user_id=user_id,
                order_number=order_number,
                woocommerce_order_id=woocommerce_order_id
            )
            session.add(order_tracking)
            session.commit()
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logging.error(f"Exception while handling an update: {context.error}")
        
        if update and hasattr(update, 'effective_message') and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "متأسفانه خطایی رخ داده است. لطفاً دوباره تلاش کنید."
                )
            except Exception:
                pass
    
    def start(self):
        """Start the bot"""
        try:
            logging.info("Starting Telegram bot...")
            self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logging.error(f"Failed to start bot: {e}")
            raise
