#!/usr/bin/env python3
"""
API Integrations Module - FREE FOREVER APIs
============================================
Round Table approved APIs for Costco Markdown Scraper v5

FREE FOREVER (No payment ever):
- Groq LLM: 14,400 req/day
- ntfy.sh: 250/day or unlimited self-hosted
- Open Food Facts: 100 req/min
- Brocade.io: Unlimited reads
- Nominatim: Free geocoding

USER PROVIDED:
- Perplexity: $5/month free credits
- Flowith: 1,000 one-time credits

Created-By: DEADMAN
Round Table: 6-0 unanimous for Notifications First
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # dotenv not installed, use os.environ directly


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class APIConfig:
    """Centralized API configuration"""

    # Groq LLM
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_ENDPOINT: str = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_DAILY_LIMIT: int = 14400

    # Perplexity
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    PERPLEXITY_ENDPOINT: str = "https://api.perplexity.ai/chat/completions"
    PERPLEXITY_MODEL: str = "sonar"  # New 2025 model names: sonar, sonar-pro, sonar-reasoning

    # Flowith
    FLOWITH_API_KEY: str = os.getenv("FLOWITH_API_KEY", "")
    FLOWITH_ENDPOINT: str = "https://api.flowith.io/v1"

    # ntfy.sh
    NTFY_TOPIC: str = os.getenv("NTFY_TOPIC", "costco-deals")
    NTFY_ENDPOINT: str = "https://ntfy.sh"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Discord
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

    # Product Data (no auth needed)
    OPEN_FOOD_FACTS_ENDPOINT: str = "https://world.openfoodfacts.org/api/v2"
    BROCADE_ENDPOINT: str = "https://www.brocade.io/api/items"


config = APIConfig()


# =============================================================================
# NOTIFICATION SERVICES (Priority #1 - Round Table Winner)
# =============================================================================

class NotificationService:
    """Unified notification service using Apprise pattern"""

    def __init__(self):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_ntfy(self, title: str, message: str, priority: str = "default") -> bool:
        """Send notification via ntfy.sh (FREE FOREVER)"""
        if not self.config.NTFY_TOPIC:
            return False

        session = await self._get_session()
        url = f"{self.config.NTFY_ENDPOINT}/{self.config.NTFY_TOPIC}"

        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": "shopping_cart,dollar"
        }

        try:
            async with session.post(url, data=message, headers=headers) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[NTFY] Error: {e}")
            return False

    async def send_telegram(self, message: str) -> bool:
        """Send notification via Telegram Bot API (FREE FOREVER)"""
        if not self.config.TELEGRAM_BOT_TOKEN or not self.config.TELEGRAM_CHAT_ID:
            return False

        session = await self._get_session()
        url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": self.config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            async with session.post(url, json=payload) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[TELEGRAM] Error: {e}")
            return False

    async def send_discord(self, title: str, message: str, color: int = 0x00FF00) -> bool:
        """Send notification via Discord Webhook (FREE FOREVER - 30/min)"""
        if not self.config.DISCORD_WEBHOOK_URL:
            return False

        session = await self._get_session()

        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        try:
            async with session.post(self.config.DISCORD_WEBHOOK_URL, json=payload) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            print(f"[DISCORD] Error: {e}")
            return False

    async def notify_all(self, title: str, message: str) -> Dict[str, bool]:
        """Send to all configured notification channels"""
        results = {}

        # ntfy.sh (primary)
        results["ntfy"] = await self.send_ntfy(title, message)

        # Telegram (if configured)
        if self.config.TELEGRAM_BOT_TOKEN:
            results["telegram"] = await self.send_telegram(f"*{title}*\n{message}")

        # Discord (if configured)
        if self.config.DISCORD_WEBHOOK_URL:
            results["discord"] = await self.send_discord(title, message)

        return results


# =============================================================================
# LLM SERVICES (Priority #2)
# =============================================================================

class LLMService:
    """LLM service using Groq (FREE) and Perplexity ($5/month credit)"""

    def __init__(self):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._groq_calls_today = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def groq_analyze(self, prompt: str, system: str = "You are a deal analysis expert.") -> Optional[str]:
        """
        Analyze using Groq LLM (FREE FOREVER - 14,400 req/day)
        Best for: deal quality analysis, categorization, parsing
        """
        if not self.config.GROQ_API_KEY:
            return None

        if self._groq_calls_today >= self.config.GROQ_DAILY_LIMIT:
            print("[GROQ] Daily limit reached")
            return None

        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {self.config.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        try:
            async with session.post(self.config.GROQ_ENDPOINT, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._groq_calls_today += 1
                    return data["choices"][0]["message"]["content"]
                else:
                    error = await resp.text()
                    print(f"[GROQ] Error {resp.status}: {error}")
                    return None
        except Exception as e:
            print(f"[GROQ] Error: {e}")
            return None

    async def perplexity_search(self, query: str) -> Optional[str]:
        """
        Search using Perplexity API ($5/month FREE credit)
        Best for: real-time web search, price research, competitor analysis
        """
        if not self.config.PERPLEXITY_API_KEY:
            return None

        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {self.config.PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.PERPLEXITY_MODEL,
            "messages": [
                {"role": "user", "content": query}
            ]
        }

        try:
            async with session.post(self.config.PERPLEXITY_ENDPOINT, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error = await resp.text()
                    print(f"[PERPLEXITY] Error {resp.status}: {error}")
                    return None
        except Exception as e:
            print(f"[PERPLEXITY] Error: {e}")
            return None

    async def analyze_deal(self, product_name: str, original_price: float,
                          markdown_price: float, category: str) -> Optional[Dict]:
        """Analyze a Costco deal using Groq"""
        discount_pct = ((original_price - markdown_price) / original_price) * 100

        prompt = f"""Analyze this Costco markdown deal:

Product: {product_name}
Category: {category}
Original Price: ${original_price:.2f}
Markdown Price: ${markdown_price:.2f}
Discount: {discount_pct:.1f}%

Rate this deal 1-10 and explain:
1. Is this a good discount for this category?
2. Is this product typically worth buying?
3. Any concerns (quality, better alternatives)?

Keep response under 100 words."""

        response = await self.groq_analyze(prompt)
        if response:
            return {
                "analysis": response,
                "discount_percent": discount_pct,
                "analyzed_at": datetime.now().isoformat()
            }
        return None


# =============================================================================
# PRODUCT DATA SERVICES (Priority #3)
# =============================================================================

class ProductDataService:
    """Product data enrichment using FREE APIs"""

    def __init__(self):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}  # Simple in-memory cache

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def lookup_barcode_openfoodfacts(self, barcode: str) -> Optional[Dict]:
        """
        Look up product by barcode using Open Food Facts (FREE FOREVER - 100 req/min)
        Best for: food products, nutrition data
        """
        # Check cache first
        cache_key = f"off_{barcode}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        session = await self._get_session()
        url = f"{self.config.OPEN_FOOD_FACTS_ENDPOINT}/product/{barcode}"

        headers = {
            "User-Agent": "CostcoMarkdownScraper/5.0 (github.com/deadman)"
        }

        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == 1:
                        product = data.get("product", {})
                        result = {
                            "name": product.get("product_name"),
                            "brand": product.get("brands"),
                            "category": product.get("categories"),
                            "image_url": product.get("image_url"),
                            "nutrition_grade": product.get("nutrition_grades"),
                            "source": "openfoodfacts"
                        }
                        self._cache[cache_key] = result
                        return result
                return None
        except Exception as e:
            print(f"[OPENFOODFACTS] Error: {e}")
            return None

    async def lookup_barcode_brocade(self, barcode: str) -> Optional[Dict]:
        """
        Look up product by barcode using Brocade.io (FREE FOREVER - unlimited reads)
        Best for: general products, UPC data
        """
        cache_key = f"brocade_{barcode}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        session = await self._get_session()
        url = f"{self.config.BROCADE_ENDPOINT}/{barcode}"

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = {
                        "name": data.get("name"),
                        "brand": data.get("brand_name"),
                        "category": data.get("category"),
                        "source": "brocade"
                    }
                    self._cache[cache_key] = result
                    return result
                return None
        except Exception as e:
            print(f"[BROCADE] Error: {e}")
            return None

    async def enrich_product(self, barcode: str) -> Optional[Dict]:
        """Try multiple sources to enrich product data"""
        # Try Open Food Facts first (best for food)
        result = await self.lookup_barcode_openfoodfacts(barcode)
        if result:
            return result

        # Fall back to Brocade
        result = await self.lookup_barcode_brocade(barcode)
        if result:
            return result

        return None


# =============================================================================
# FLOWITH SERVICE (AI Agents)
# =============================================================================

class FlowithService:
    """Flowith.io AI agent service (1,000 free credits)"""

    def __init__(self):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def query(self, prompt: str) -> Optional[str]:
        """Query Flowith API"""
        if not self.config.FLOWITH_API_KEY:
            return None

        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {self.config.FLOWITH_API_KEY}",
            "Content-Type": "application/json"
        }

        # Note: Flowith API structure may vary - check their docs
        payload = {
            "prompt": prompt
        }

        try:
            async with session.post(f"{self.config.FLOWITH_ENDPOINT}/query",
                                   json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response")
                else:
                    error = await resp.text()
                    print(f"[FLOWITH] Error {resp.status}: {error}")
                    return None
        except Exception as e:
            print(f"[FLOWITH] Error: {e}")
            return None


# =============================================================================
# UNIFIED API MANAGER
# =============================================================================

class APIManager:
    """Unified manager for all API integrations"""

    def __init__(self):
        self.notifications = NotificationService()
        self.llm = LLMService()
        self.products = ProductDataService()
        self.flowith = FlowithService()

    async def close_all(self):
        """Close all API sessions"""
        await self.notifications.close()
        await self.llm.close()
        await self.products.close()
        await self.flowith.close()

    def get_status(self) -> Dict[str, bool]:
        """Check which APIs are configured"""
        return {
            "groq": bool(config.GROQ_API_KEY),
            "perplexity": bool(config.PERPLEXITY_API_KEY),
            "flowith": bool(config.FLOWITH_API_KEY),
            "ntfy": bool(config.NTFY_TOPIC),
            "telegram": bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID),
            "discord": bool(config.DISCORD_WEBHOOK_URL),
            "openfoodfacts": True,  # Always available (no auth)
            "brocade": True,  # Always available (no auth)
        }

    async def notify_deal(self, product_name: str, original_price: float,
                         markdown_price: float, warehouse: str,
                         analyze: bool = True) -> Dict:
        """Send deal notification with optional LLM analysis"""
        discount_pct = ((original_price - markdown_price) / original_price) * 100

        # Build notification message
        title = f"Costco Deal: {discount_pct:.0f}% OFF!"
        message = f"""
{product_name}
Was: ${original_price:.2f} -> Now: ${markdown_price:.2f}
Savings: ${original_price - markdown_price:.2f} ({discount_pct:.1f}%)
Location: {warehouse}
"""

        # Get LLM analysis if requested
        analysis = None
        if analyze and config.GROQ_API_KEY:
            analysis = await self.llm.analyze_deal(
                product_name, original_price, markdown_price, "Unknown"
            )
            if analysis:
                message += f"\nAI Analysis: {analysis['analysis'][:200]}"

        # Send notifications
        notify_results = await self.notifications.notify_all(title, message.strip())

        return {
            "notified": notify_results,
            "analysis": analysis,
            "discount_percent": discount_pct
        }


# =============================================================================
# CLI TESTING
# =============================================================================

async def test_apis():
    """Test all configured APIs"""
    print("=" * 60)
    print("API Integration Test")
    print("=" * 60)

    manager = APIManager()

    # Check status
    status = manager.get_status()
    print("\nAPI Configuration Status:")
    for api, configured in status.items():
        icon = "[OK]" if configured else "[--]"
        print(f"  {icon} {api}")

    # Test ntfy
    print("\n[TEST] ntfy.sh notification...")
    result = await manager.notifications.send_ntfy(
        "Test Alert",
        "This is a test from Costco Markdown Scraper v5",
        "low"
    )
    print(f"  Result: {'Success' if result else 'Failed/Not configured'}")

    # Test Groq
    if config.GROQ_API_KEY:
        print("\n[TEST] Groq LLM...")
        result = await manager.llm.groq_analyze("What makes a good Costco deal?")
        print(f"  Result: {result[:100] if result else 'Failed'}...")

    # Test Perplexity
    if config.PERPLEXITY_API_KEY:
        print("\n[TEST] Perplexity search...")
        result = await manager.llm.perplexity_search("Current Costco deals January 2026")
        print(f"  Result: {result[:100] if result else 'Failed'}...")

    # Test Open Food Facts
    print("\n[TEST] Open Food Facts (barcode: 0099482439354)...")
    result = await manager.products.lookup_barcode_openfoodfacts("0099482439354")
    print(f"  Result: {result if result else 'Not found'}")

    await manager.close_all()
    print("\nTest complete!")


if __name__ == "__main__":
    asyncio.run(test_apis())
