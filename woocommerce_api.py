import requests
import logging
from typing import List, Dict, Optional
from config import Config

class WooCommerceAPI:
    """WooCommerce REST API client"""
    
    def __init__(self):
        self.base_url = Config.WOOCOMMERCE_URL
        self.consumer_key = Config.WOOCOMMERCE_CONSUMER_KEY
        self.consumer_secret = Config.WOOCOMMERCE_CONSUMER_SECRET
        
        if not all([self.base_url, self.consumer_key, self.consumer_secret]):
            raise ValueError("WooCommerce API credentials are not properly configured")
        
        # Remove trailing slash and add API endpoint
        self.api_url = f"{self.base_url.rstrip('/')}/wp-json/wc/v3"
        
        self.auth = (self.consumer_key, self.consumer_secret)
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TelegramBot/1.0'
        }
        
        logging.info(f"WooCommerce API initialized for: {self.base_url}")
    
    def _make_request(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """Make a request to WooCommerce API"""
        url = f"{self.api_url}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"WooCommerce API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"WooCommerce API request failed: {e}")
            return None
    
    def get_categories(self, per_page: int = 50) -> List[Dict]:
        """Get product categories"""
        params = {
            'per_page': per_page,
            'orderby': 'name',
            'order': 'asc'
        }
        
        categories = self._make_request('products/categories', params=params)
        
        if categories is None:
            logging.error("Failed to fetch categories from WooCommerce")
            return []
        
        # Filter out categories with no products
        return [cat for cat in categories if cat.get('count', 0) > 0]
    
    def get_products(self, category_id: int = None, per_page: int = 20, page: int = 1) -> List[Dict]:
        """Get products, optionally filtered by category"""
        params = {
            'per_page': per_page,
            'page': page,
            'status': 'publish',
            'orderby': 'popularity',
            'order': 'desc'
        }
        
        if category_id:
            params['category'] = category_id
        
        products = self._make_request('products', params=params)
        
        if products is None:
            logging.error("Failed to fetch products from WooCommerce")
            return []
        
        return products
    
    def get_product(self, product_id: int) -> Optional[Dict]:
        """Get a specific product by ID"""
        product = self._make_request(f'products/{product_id}')
        
        if product is None:
            logging.error(f"Failed to fetch product {product_id} from WooCommerce")
        
        return product
    
    def search_products(self, search_term: str, per_page: int = 20) -> List[Dict]:
        """Search for products"""
        params = {
            'search': search_term,
            'per_page': per_page,
            'status': 'publish'
        }
        
        products = self._make_request('products', params=params)
        
        if products is None:
            logging.error(f"Failed to search products for term: {search_term}")
            return []
        
        return products
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        """Get order details by ID"""
        order = self._make_request(f'orders/{order_id}')
        
        if order is None:
            logging.error(f"Failed to fetch order {order_id} from WooCommerce")
        
        return order
    
    def search_order_by_number(self, order_number: str) -> Optional[Dict]:
        """Search for order by order number"""
        params = {
            'search': order_number,
            'per_page': 1
        }
        
        orders = self._make_request('orders', params=params)
        
        if orders and len(orders) > 0:
            return orders[0]
        
        logging.info(f"No order found with number: {order_number}")
        return None
    
    def format_product_message(self, product: Dict, language: str = 'fa') -> str:
        """Format product information for Telegram message"""
        try:
            name = product.get('name', 'Unknown Product')
            price = product.get('price', '0')
            currency = 'تومان' if language == 'fa' else 'USD'
            stock_status = product.get('stock_status', 'outofstock')
            description = product.get('short_description', '')
            
            # Remove HTML tags from description
            import re
            description = re.sub('<.*?>', '', description).strip()
            
            stock_text = 'موجود' if stock_status == 'instock' else 'ناموجود'
            if language == 'en':
                stock_text = 'In Stock' if stock_status == 'instock' else 'Out of Stock'
            
            message = f"🛍️ **{name}**\n\n"
            
            if description:
                message += f"{description[:200]}...\n\n" if len(description) > 200 else f"{description}\n\n"
            
            message += f"💰 قیمت: {price} {currency}\n" if language == 'fa' else f"💰 Price: {price} {currency}\n"
            message += f"📦 وضعیت: {stock_text}\n" if language == 'fa' else f"📦 Status: {stock_text}\n"
            
            # Add product URL if available
            if product.get('permalink'):
                message += f"\n🔗 لینک محصول: {product['permalink']}"
            
            return message
            
        except Exception as e:
            logging.error(f"Error formatting product message: {e}")
            return "خطا در نمایش اطلاعات محصول" if language == 'fa' else "Error displaying product information"
    
    def format_order_message(self, order: Dict, language: str = 'fa') -> str:
        """Format order information for Telegram message"""
        try:
            order_number = order.get('number', 'Unknown')
            status = order.get('status', 'unknown')
            total = order.get('total', '0')
            currency = order.get('currency', 'USD')
            date_created = order.get('date_created', '')
            
            # Map order status to Persian
            status_map_fa = {
                'pending': 'در انتظار پرداخت',
                'processing': 'در حال پردازش',
                'on-hold': 'در انتظار',
                'completed': 'تکمیل شده',
                'cancelled': 'لغو شده',
                'refunded': 'برگشت داده شده',
                'failed': 'ناموفق'
            }
            
            status_map_en = {
                'pending': 'Pending Payment',
                'processing': 'Processing',
                'on-hold': 'On Hold',
                'completed': 'Completed',
                'cancelled': 'Cancelled',
                'refunded': 'Refunded',
                'failed': 'Failed'
            }
            
            status_text = status_map_fa.get(status, status) if language == 'fa' else status_map_en.get(status, status)
            
            if language == 'fa':
                message = f"📦 **سفارش #{order_number}**\n\n"
                message += f"🔄 وضعیت: {status_text}\n"
                message += f"💰 مجموع: {total} {currency}\n"
                if date_created:
                    message += f"📅 تاریخ سفارش: {date_created[:10]}\n"
            else:
                message = f"📦 **Order #{order_number}**\n\n"
                message += f"🔄 Status: {status_text}\n"
                message += f"💰 Total: {total} {currency}\n"
                if date_created:
                    message += f"📅 Order Date: {date_created[:10]}\n"
            
            # Add line items
            line_items = order.get('line_items', [])
            if line_items:
                message += f"\n🛍️ آیتم‌های سفارش:\n" if language == 'fa' else f"\n🛍️ Order Items:\n"
                for item in line_items[:5]:  # Show max 5 items
                    quantity = item.get('quantity', 1)
                    name = item.get('name', 'Unknown Item')
                    message += f"• {quantity}x {name}\n"
                
                if len(line_items) > 5:
                    remaining = len(line_items) - 5
                    message += f"... و {remaining} آیتم دیگر\n" if language == 'fa' else f"... and {remaining} more items\n"
            
            return message
            
        except Exception as e:
            logging.error(f"Error formatting order message: {e}")
            return "خطا در نمایش اطلاعات سفارش" if language == 'fa' else "Error displaying order information"
