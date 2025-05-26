import json
import os
import logging
from typing import Dict, Optional, List
from openai import OpenAI
import requests
from config import Config, MESSAGES

class AIService:
    """AI service for handling customer conversations"""
    
    def __init__(self):
        self.use_local_ai = Config.USE_LOCAL_AI
        self.ollama_url = Config.OLLAMA_URL
        self.local_model = Config.LOCAL_AI_MODEL
        
        if self.use_local_ai:
            # Test Ollama connection
            try:
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    logging.info(f"AI Service initialized with local Ollama model: {self.local_model}")
                else:
                    logging.warning("Ollama not available, falling back to OpenAI")
                    self.use_local_ai = False
            except requests.exceptions.RequestException:
                logging.warning("Ollama not available, falling back to OpenAI")
                self.use_local_ai = False
        
        if not self.use_local_ai:
            self.api_key = Config.OPENAI_API_KEY
            if not self.api_key:
                raise ValueError("Neither local AI nor OpenAI API key is configured")
            
            self.client = OpenAI(api_key=self.api_key)
            self.model = Config.AI_MODEL
            logging.info("AI Service initialized with OpenAI GPT-4o")
        
        self.max_tokens = Config.AI_MAX_TOKENS
        self.temperature = Config.AI_TEMPERATURE
    
    def generate_response(self, user_message: str, conversation_context: List[Dict] = None, language: str = 'fa') -> Dict:
        """
        Generate AI response for customer message
        
        Args:
            user_message: The user's message
            conversation_context: Previous messages in the conversation
            language: Language code ('fa' or 'en')
        
        Returns:
            Dict with 'response', 'confidence', 'should_escalate', 'intent'
        """
        try:
            if self.use_local_ai:
                return self._generate_local_response(user_message, conversation_context, language)
            else:
                return self._generate_openai_response(user_message, conversation_context, language)
            
        except Exception as e:
            logging.error(f"AI service error: {e}")
            return self._fallback_response(language)
    
    def _generate_openai_response(self, user_message: str, conversation_context: List[Dict], language: str) -> Dict:
        """Generate response using OpenAI"""
        # Build conversation history
        messages = self._build_conversation_context(user_message, conversation_context, language)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )
        
        # Parse AI response
        ai_response = json.loads(response.choices[0].message.content)
        
        # Validate and structure response
        return {
            'response': ai_response.get('response', ''),
            'confidence': max(0.0, min(1.0, ai_response.get('confidence', 0.5))),
            'should_escalate': ai_response.get('should_escalate', False),
            'intent': ai_response.get('intent', 'general_inquiry'),
            'suggested_actions': ai_response.get('suggested_actions', [])
        }
    
    def _generate_local_response(self, user_message: str, conversation_context: List[Dict], language: str) -> Dict:
        """Generate response using local Ollama"""
        # Build conversation context
        prompt = self._build_local_prompt(user_message, conversation_context, language)
        
        # Make request to Ollama
        ollama_request = {
            "model": self.local_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json=ollama_request,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama request failed: {response.status_code}")
        
        ollama_response = response.json()
        response_text = ollama_response.get('response', '')
        
        # Try to parse as JSON, fallback to plain text
        try:
            ai_response = json.loads(response_text)
            return {
                'response': ai_response.get('response', response_text),
                'confidence': max(0.0, min(1.0, ai_response.get('confidence', 0.7))),
                'should_escalate': ai_response.get('should_escalate', False),
                'intent': ai_response.get('intent', 'general_inquiry'),
                'suggested_actions': ai_response.get('suggested_actions', [])
            }
        except json.JSONDecodeError:
            # If not JSON, treat as plain response
            return {
                'response': response_text,
                'confidence': 0.7,
                'should_escalate': False,
                'intent': 'general_inquiry',
                'suggested_actions': []
            }
    
    def _build_local_prompt(self, user_message: str, context: List[Dict], language: str) -> str:
        """Build prompt for local AI model"""
        system_prompt = self._get_system_prompt(language)
        
        # Build conversation history
        conversation_history = ""
        if context:
            for msg in context[-5:]:  # Last 5 messages for local AI
                role = "کاربر" if msg.get('is_from_user') else "دستیار"
                if language == 'en':
                    role = "User" if msg.get('is_from_user') else "Assistant"
                conversation_history += f"{role}: {msg.get('content', '')}\n"
        
        # Create full prompt
        full_prompt = f"""{system_prompt}

{conversation_history}
{"کاربر" if language == 'fa' else "User"}: {user_message}
{"دستیار" if language == 'fa' else "Assistant"}:"""
        
        return full_prompt
    
    def _build_conversation_context(self, user_message: str, context: List[Dict], language: str) -> List[Dict]:
        """Build conversation context for AI model"""
        
        system_prompt = self._get_system_prompt(language)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 10 messages)
        if context:
            for msg in context[-10:]:
                role = "user" if msg.get('is_from_user') else "assistant"
                messages.append({
                    "role": role,
                    "content": msg.get('content', '')
                })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt based on language"""
        
        if language == 'fa':
            return """
شما یک دستیار هوشمند برای فروشگاه آنلاین هستید که به زبان فارسی پاسخ می‌دهید.

ویژگی‌های شما:
- پاسخ‌های مفید، دقیق و مودبانه ارائه دهید
- در مورد محصولات، قیمت‌ها، و خدمات فروشگاه اطلاعات دهید
- سوالات در مورد سفارشات، ارسال و بازگشت کالا را پاسخ دهید
- اگر نمی‌توانید پاسخ دقیق بدهید، به پشتیبانی انسانی ارجاع دهید

قوانین مهم:
- همیشه به زبان فارسی پاسخ دهید
- مودب و دوستانه باشید
- اگر اطمینان کم دارید، should_escalate را true کنید
- پاسخ‌تان را در قالب JSON ارائه دهید

فرمت پاسخ JSON:
{
    "response": "پاسخ شما به زبان فارسی",
    "confidence": 0.8,
    "should_escalate": false,
    "intent": "product_inquiry",
    "suggested_actions": ["view_products", "contact_support"]
}

انواع intent:
- product_inquiry: سوال در مورد محصولات
- order_tracking: پیگیری سفارش
- support_request: درخواست پشتیبانی
- category_browse: مرور دسته‌بندی‌ها
- general_inquiry: سوال عمومی
- complaint: شکایت
- compliment: تشکر یا تمجید
"""
        else:
            return """
You are an intelligent assistant for an online store that responds in English.

Your capabilities:
- Provide helpful, accurate, and polite responses
- Give information about products, prices, and store services
- Answer questions about orders, shipping, and returns
- Escalate to human support when you cannot provide accurate answers

Important rules:
- Always respond in English
- Be polite and friendly
- If you have low confidence, set should_escalate to true
- Provide your response in JSON format

JSON Response Format:
{
    "response": "Your response in English",
    "confidence": 0.8,
    "should_escalate": false,
    "intent": "product_inquiry",
    "suggested_actions": ["view_products", "contact_support"]
}

Intent types:
- product_inquiry: Questions about products
- order_tracking: Order tracking requests
- support_request: Support requests
- category_browse: Category browsing
- general_inquiry: General questions
- complaint: Customer complaints
- compliment: Thanks or praise
"""
    
    def _fallback_response(self, language: str) -> Dict:
        """Fallback response when AI service fails"""
        if language == 'fa':
            return {
                'response': 'متأسفانه در حال حاضر نمی‌توانم پاسخ مناسب ارائه دهم. لطفاً با پشتیبانی تماس بگیرید.',
                'confidence': 0.0,
                'should_escalate': True,
                'intent': 'support_request',
                'suggested_actions': ['contact_support']
            }
        else:
            return {
                'response': 'I apologize, but I cannot provide a suitable response right now. Please contact our support team.',
                'confidence': 0.0,
                'should_escalate': True,
                'intent': 'support_request',
                'suggested_actions': ['contact_support']
            }
    
    def analyze_intent(self, message: str, language: str = 'fa') -> Dict:
        """Analyze user message intent for routing purposes"""
        try:
            prompt = self._get_intent_analysis_prompt(message, language)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                'intent': result.get('intent', 'general_inquiry'),
                'confidence': max(0.0, min(1.0, result.get('confidence', 0.5))),
                'entities': result.get('entities', {}),
                'suggested_action': result.get('suggested_action', 'respond_normally')
            }
            
        except Exception as e:
            logging.error(f"Intent analysis error: {e}")
            return {
                'intent': 'general_inquiry',
                'confidence': 0.5,
                'entities': {},
                'suggested_action': 'respond_normally'
            }
    
    def _get_intent_analysis_prompt(self, message: str, language: str) -> str:
        """Get prompt for intent analysis"""
        if language == 'fa':
            return f"""
پیام کاربر را تجزیه و تحلیل کنید و intent آن را مشخص کنید:

پیام: "{message}"

انواع intent:
- product_inquiry: سوال در مورد محصولات
- order_tracking: پیگیری سفارش (شامل شماره سفارش)
- category_browse: مرور دسته‌بندی‌ها
- support_request: درخواست پشتیبانی
- general_inquiry: سوال عمومی
- complaint: شکایت
- compliment: تشکر

پاسخ در قالب JSON:
{{
    "intent": "intent_type",
    "confidence": 0.8,
    "entities": {{"order_number": "123", "product_name": "تی شرت"}},
    "suggested_action": "show_categories"
}}
"""
        else:
            return f"""
Analyze the user message and identify its intent:

Message: "{message}"

Intent types:
- product_inquiry: Questions about products
- order_tracking: Order tracking (includes order number)
- category_browse: Category browsing
- support_request: Support requests
- general_inquiry: General questions
- complaint: Customer complaints
- compliment: Thanks or praise

Response in JSON format:
{{
    "intent": "intent_type",
    "confidence": 0.8,
    "entities": {{"order_number": "123", "product_name": "T-shirt"}},
    "suggested_action": "show_categories"
}}
"""
    
    def summarize_conversation(self, messages: List[Dict], language: str = 'fa') -> str:
        """Generate a summary of the conversation for analytics"""
        try:
            conversation_text = "\n".join([
                f"{'کاربر' if msg.get('is_from_user') else 'ربات'}: {msg.get('content', '')}"
                for msg in messages[-10:]  # Last 10 messages
            ])
            
            prompt = f"""
خلاصه‌ای از مکالمه زیر ارائه دهید:

{conversation_text}

خلاصه شما باید شامل:
- موضوع اصلی مکالمه
- نتیجه یا وضعیت نهایی
- سطح رضایت احتمالی مشتری

پاسخ کوتاه و مفید ارائه دهید.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Conversation summary error: {e}")
            return "خلاصه مکالمه در دسترس نیست" if language == 'fa' else "Conversation summary not available"
