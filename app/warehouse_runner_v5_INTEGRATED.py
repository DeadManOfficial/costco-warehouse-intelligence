#!/usr/bin/env python3
"""
Warehouse Runner v5 INTEGRATED - Full Stack Markdown Hunter
============================================================
Combines Round Table winning strategy with all research:

1. AUTOMATION INTEGRATION (Option B - Winner)
   - Health monitoring with state tracking
   - Circuit breaker for failure handling
   - Discord/Slack alerting
   - Heartbeat for liveness
   - State recovery for crash resilience

2. AMAZON PRICE COMPARISON (Canopy API)
   - Compare Costco markdown vs Amazon price
   - Calculate true savings
   - Flag when Amazon is cheaper

3. COSTCO API REFERENCE
   - GraphQL endpoint: ecom-api.costco.com (authenticated)
   - Instacart API for same-day inventory
   - Price code detection (.97, .00, .88, asterisk)

4. FREE FOREVER API INTEGRATIONS (Round Table: 6-0 unanimous)
   - Notifications: ntfy.sh (250/day), Telegram (unlimited), Discord (30/min)
   - LLM Analysis: Groq (14,400 req/day FREE), Perplexity ($5/mo credit)
   - Product Data: Open Food Facts (100 req/min), Brocade.io (unlimited)
   - AI Agents: Flowith (1,000 free credits)

Created-By: DEADMAN
Round Table: 6-1 vote for Automation First strategy
FREE API Round Table: 6-0 unanimous for Notifications First
Research: 17 specialist agents + 8 FREE API research agents
"""

import json
import argparse
import sys
import asyncio
import aiohttp
import random
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import time
import os

# Add paths for imports - LOCAL FIRST to avoid loading old geocoder from DeadMan_AI_Research
sys.path.insert(0, str(Path(__file__).parent))  # Local src/ directory (has updated geocoder)

# Add DeadMan_AI_Research AFTER local for automation components only
_deadman_scripts = str(Path(__file__).parent.parent.parent / "DeadMan_AI_Research" / "Scripts")
if _deadman_scripts not in sys.path:
    sys.path.append(_deadman_scripts)  # APPEND not INSERT to keep local geocoder priority

# Try to import automation components
try:
    from automation.health_monitor import HealthState, HealthStatus, ScrapeMetrics
    from automation.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
    from automation.heartbeat import Heartbeat
    from automation.state_recovery import StateManager
    from automation.alert_config import setup_console_alerts
    from automation.alerting import AlertSeverity
    from automation.logger import setup_logging
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False
    print("[WARN] Automation components not available - running in standalone mode")

from costco_geocoder_v2 import CostcoGeocoderV2

# Try to import API integrations (FREE FOREVER APIs)
try:
    from api_integrations import APIManager, config as api_config
    API_INTEGRATIONS_AVAILABLE = True
except ImportError:
    API_INTEGRATIONS_AVAILABLE = False
    print("[WARN] API integrations not available - run: pip install python-dotenv apprise")


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Configuration for v5 integrated scraper"""

    # Canopy API (Amazon data)
    CANOPY_API_KEY = os.getenv("CANOPY_API_KEY", "")
    CANOPY_GRAPHQL_ENDPOINT = "https://graphql.canopyapi.co/"
    CANOPY_REST_ENDPOINT = "https://rest.canopyapi.co/api/amazon"

    # Costco API (authenticated - for reference)
    COSTCO_GRAPHQL_ENDPOINT = "https://ecom-api.costco.com/ebusiness/order/v1/orders/graphql"
    COSTCO_SEARCH_ENDPOINT = "https://search.costco.com/api/apps/www_costco_com/query/www_costco_com_search"

    # Rate limiting
    MIN_REQUEST_DELAY = 2.0
    MAX_CONCURRENT_REQUESTS = 5

    # Alerting thresholds
    ALERT_ON_DEEP_DISCOUNT_PERCENT = 50
    ALERT_ON_AMAZON_CHEAPER = True


# =============================================================================
# PRICE CODE INTELLIGENCE
# =============================================================================

class PriceCode(Enum):
    """Costco price code meanings"""
    FULL_PRICE = ".99"
    CORPORATE_CLEARANCE = ".97"
    MANAGER_SPECIAL = ".00"
    MANAGER_MARKDOWN = ".88"
    PROMO_PRICE = ".49"


MARKDOWN_MONDAY_2026 = [
    "2026-01-05", "2026-02-02", "2026-03-02", "2026-03-30",
    "2026-04-27", "2026-05-25", "2026-06-22", "2026-07-20",
    "2026-08-17", "2026-09-14", "2026-10-12", "2026-11-09", "2026-12-07"
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AmazonComparison:
    """Amazon price comparison data"""
    amazon_price: Optional[float] = None
    amazon_url: Optional[str] = None
    amazon_available: bool = False
    price_delta: float = 0.0  # Costco - Amazon (negative = Costco cheaper)
    costco_is_better: bool = True
    comparison_timestamp: str = ""
    error: Optional[str] = None


@dataclass
class MarkdownItem:
    """Enhanced markdown item with Amazon comparison"""
    product_id: str
    name: str
    original_price: float
    markdown_price: float
    price_code: str
    discount_percent: float
    category: str
    warehouse_number: int
    warehouse_city: str
    warehouse_state: str
    warehouse_zip: str
    has_asterisk: bool
    tag_date: Optional[str]
    discovered_at: str
    markdown_monday: bool
    # Amazon comparison
    amazon: Optional[AmazonComparison] = None


@dataclass
class ScraperState:
    """Scraper state for recovery"""
    session_id: str
    start_time: str
    items_processed: int = 0
    markdowns_found: int = 0
    errors: List[str] = field(default_factory=list)
    last_checkpoint: str = ""


# =============================================================================
# AMAZON PRICE COMPARISON (Canopy API)
# =============================================================================

class AmazonPriceChecker:
    """
    Compare prices with Amazon via Canopy GraphQL API.

    Requires CANOPY_API_KEY environment variable.
    Free tier: Limited requests
    Docs: https://docs.canopyapi.co/
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.CANOPY_API_KEY
        self.enabled = bool(self.api_key)
        self._session: Optional[aiohttp.ClientSession] = None

        if not self.enabled:
            print("[INFO] Amazon comparison disabled - no CANOPY_API_KEY set")

    async def __aenter__(self):
        if self.enabled:
            self._session = aiohttp.ClientSession(
                headers={
                    "API-KEY": self.api_key,
                    "Content-Type": "application/json"
                }
            )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def search_product(self, product_name: str) -> AmazonComparison:
        """
        Search Amazon for a product and get price.

        Uses Canopy GraphQL API to search Amazon.com
        """
        if not self.enabled or not self._session:
            return AmazonComparison(error="API not configured")

        # GraphQL query for Amazon search
        query = """
        query SearchProducts($query: String!, $domain: AmazonDomain!) {
            amazonProductSearchResults(input: {searchQuery: $query, domain: $domain, page: 1}) {
                results {
                    asin
                    title
                    price {
                        display
                        value
                        currency
                    }
                    url
                }
            }
        }
        """

        variables = {
            "query": product_name,
            "domain": "AMAZON_US"
        }

        try:
            async with self._session.post(
                Config.CANOPY_GRAPHQL_ENDPOINT,
                json={"query": query, "variables": variables}
            ) as response:
                if response.status != 200:
                    return AmazonComparison(error=f"API error: {response.status}")

                data = await response.json()

                if "errors" in data:
                    return AmazonComparison(error=str(data["errors"]))

                results = data.get("data", {}).get("amazonProductSearchResults", {}).get("results", [])

                if not results:
                    return AmazonComparison(amazon_available=False)

                # Get first result
                first = results[0]
                price_data = first.get("price", {})

                return AmazonComparison(
                    amazon_price=price_data.get("value"),
                    amazon_url=first.get("url"),
                    amazon_available=True,
                    comparison_timestamp=datetime.now().isoformat()
                )

        except Exception as e:
            return AmazonComparison(error=str(e))

    def calculate_comparison(self, costco_price: float, amazon: AmazonComparison) -> AmazonComparison:
        """Calculate price delta between Costco and Amazon"""
        if amazon.amazon_price:
            amazon.price_delta = round(costco_price - amazon.amazon_price, 2)
            amazon.costco_is_better = amazon.price_delta < 0
        return amazon


# =============================================================================
# MAIN SCRAPER CLASS
# =============================================================================

class WarehouseRunnerV5:
    """
    v5 INTEGRATED Warehouse Runner

    Features:
    - Automation integration (health, alerts, recovery)
    - Amazon price comparison
    - Price code intelligence
    - Markdown Monday awareness
    - Geographic warehouse data
    """

    def __init__(self, db_path: Optional[str] = None, use_automation: bool = True):
        """
        Initialize v5 integrated scraper.

        Args:
            db_path: Path to warehouse database
            use_automation: Enable automation components
        """
        # Find database - use absolute path
        if db_path is None:
            db_path = "D:/costco-warehouse-intelligence/data/costco_warehouses_master.json"

        if not Path(db_path).exists():
            raise FileNotFoundError(f"Warehouse database not found: {db_path}")

        # Core components
        self.geocoder = CostcoGeocoderV2(db_path)
        self.discovered_markdowns: List[MarkdownItem] = []
        self.alerts_generated: List[dict] = []

        # Automation components (if available)
        self.use_automation = use_automation and AUTOMATION_AVAILABLE
        if self.use_automation:
            self._init_automation()
        else:
            self.health_state = None
            self.circuit_breaker = None
            self.heartbeat = None
            self.state_manager = None
            self.alert_manager = None
            self.logger = None

        # State
        self.state = ScraperState(
            session_id=hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
            start_time=datetime.now().isoformat()
        )

        # API Integrations (FREE FOREVER)
        self.api_manager = None
        self.use_api_integrations = API_INTEGRATIONS_AVAILABLE
        if self.use_api_integrations:
            self.api_manager = APIManager()

        # Print status
        stats = self.geocoder.get_statistics()
        print(f"[v5 INTEGRATED] Initialized with {stats['database']['total_warehouses']} warehouses")
        print(f"[v5 INTEGRATED] Automation: {'ENABLED' if self.use_automation else 'DISABLED'}")
        print(f"[v5 INTEGRATED] Amazon comparison: {'ENABLED' if Config.CANOPY_API_KEY else 'DISABLED'}")

        # Show API integration status
        if self.use_api_integrations:
            api_status = self.api_manager.get_status()
            enabled_apis = [k for k, v in api_status.items() if v]
            print(f"[v5 INTEGRATED] APIs enabled: {', '.join(enabled_apis) if enabled_apis else 'none'}")

        if self._is_markdown_monday():
            print(">>> TODAY IS MARKDOWN MONDAY <<<")

    def _init_automation(self):
        """Initialize automation components"""
        try:
            self.logger = setup_logging("warehouse_runner_v5")
            self.health_state = HealthState()
            self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=300)
            self.heartbeat = Heartbeat(interval_seconds=30)
            self.state_manager = StateManager()
            self.alert_manager = setup_console_alerts()

            # Start heartbeat
            self.heartbeat.start()
            self.state_manager.start_run()

            if self.logger:
                self.logger.info("Automation components initialized")
        except Exception as e:
            print(f"[WARN] Failed to initialize automation: {e}")
            self.use_automation = False

    def _is_markdown_monday(self, date: Optional[datetime] = None) -> bool:
        """Check if date is Markdown Monday"""
        check_date = date or datetime.now()
        return check_date.strftime("%Y-%m-%d") in MARKDOWN_MONDAY_2026

    def _detect_price_code(self, price: float) -> Tuple[str, str]:
        """Detect Costco price code"""
        price_str = f"{price:.2f}"

        if price_str.endswith(".99"):
            return (".99", "full_price")
        elif price_str.endswith(".97"):
            return (".97", "corporate_clearance")
        elif price_str.endswith(".00"):
            return (".00", "manager_special")
        elif price_str.endswith(".88"):
            return (".88", "manager_markdown")
        elif price_str.endswith(".49") or price_str.endswith(".79"):
            return (price_str[-3:], "promotional")
        return (price_str[-3:], "unknown")

    def _categorize_product(self, name: str) -> str:
        """Categorize product by name"""
        name_lower = name.lower()

        categories = {
            "Tech/Electronics": ["tv", "laptop", "computer", "phone", "tablet", "camera", "speaker", "headphone", "monitor", "printer", "samsung", "lg", "apple", "sony", "bose"],
            "Tools/Hardware": ["tool", "drill", "saw", "wrench", "hammer", "craftsman", "dewalt", "milwaukee"],
            "Food/Grocery": ["food", "snack", "coffee", "water", "juice", "meat", "cheese", "organic", "kirkland"],
            "Home/Garden": ["furniture", "chair", "table", "bed", "mattress", "pillow", "towel", "patio", "grill"],
            "Clothing/Apparel": ["shirt", "pant", "jacket", "coat", "shoe", "dress", "jeans"],
            "Health/Beauty": ["vitamin", "supplement", "lotion", "shampoo", "health", "beauty"],
            "Office/School": ["paper", "pen", "notebook", "desk", "office", "printer paper"],
            "Sports/Outdoor": ["bike", "golf", "tennis", "camping", "fitness", "yoga"]
        }

        for category, keywords in categories.items():
            if any(kw in name_lower for kw in keywords):
                return category
        return "Other"

    async def process_with_amazon_comparison(
        self,
        product_data: dict,
        warehouse_num: int,
        amazon_checker: Optional[AmazonPriceChecker] = None
    ) -> Optional[MarkdownItem]:
        """
        Process product data with optional Amazon comparison.

        Args:
            product_data: Product info dict
            warehouse_num: Warehouse number
            amazon_checker: Optional Amazon price checker

        Returns:
            MarkdownItem if markdown detected, None otherwise
        """
        current_price = product_data.get("current_price", 0)
        original_price = product_data.get("original_price", current_price)

        # Detect price code
        code, meaning = self._detect_price_code(current_price)

        # Skip full price items
        if meaning == "full_price" and original_price == current_price:
            return None

        # Get warehouse info
        warehouse = self.geocoder.get_warehouse(warehouse_num)
        if not warehouse:
            return None

        # Calculate discount
        discount = 0.0
        if original_price > 0:
            discount = round(((original_price - current_price) / original_price) * 100, 1)

        # Create markdown item
        item = MarkdownItem(
            product_id=product_data.get("product_id", hashlib.md5(
                product_data.get("name", "").encode()).hexdigest()[:8]),
            name=product_data.get("name", "Unknown"),
            original_price=original_price,
            markdown_price=current_price,
            price_code=code,
            discount_percent=discount,
            category=self._categorize_product(product_data.get("name", "")),
            warehouse_number=warehouse_num,
            warehouse_city=warehouse.city,
            warehouse_state=warehouse.state,
            warehouse_zip=warehouse.zip,
            has_asterisk=product_data.get("has_asterisk", False),
            tag_date=product_data.get("tag_date"),
            discovered_at=datetime.now().isoformat(),
            markdown_monday=self._is_markdown_monday()
        )

        # Amazon comparison if enabled
        if amazon_checker and amazon_checker.enabled:
            amazon = await amazon_checker.search_product(item.name)
            if amazon.amazon_price:
                amazon = amazon_checker.calculate_comparison(item.markdown_price, amazon)
            item.amazon = amazon

            # Alert if Amazon is cheaper
            if amazon.amazon_price and not amazon.costco_is_better and Config.ALERT_ON_AMAZON_CHEAPER:
                self._generate_alert(
                    "amazon_cheaper",
                    item,
                    f"Amazon is ${abs(amazon.price_delta):.2f} cheaper for {item.name}"
                )

        # Generate alerts for significant finds
        self._check_alerts(item)

        self.discovered_markdowns.append(item)
        self.state.markdowns_found += 1

        # Update automation state
        if self.use_automation:
            self._update_automation_state(item)

        return item

    def _check_alerts(self, item: MarkdownItem):
        """Check if item warrants alerts"""
        # Deep discount
        if item.discount_percent >= Config.ALERT_ON_DEEP_DISCOUNT_PERCENT:
            self._generate_alert(
                "deep_discount",
                item,
                f"DEEP DISCOUNT: {item.name} is {item.discount_percent}% off!"
            )

        # Death star
        if item.has_asterisk:
            self._generate_alert(
                "death_star",
                item,
                f"DEATH STAR: {item.name} won't be restocked!"
            )

        # Manager special
        if item.price_code == ".00":
            self._generate_alert(
                "manager_special",
                item,
                f"MANAGER SPECIAL: {item.name} at ${item.markdown_price:.2f} - negotiable!"
            )

    def _generate_alert(self, alert_type: str, item: MarkdownItem, message: str):
        """Generate and store alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "item": asdict(item),
            "timestamp": datetime.now().isoformat()
        }
        self.alerts_generated.append(alert)

        # Send via automation if available
        if self.use_automation and self.alert_manager:
            severity = AlertSeverity.WARNING
            if alert_type == "deep_discount":
                severity = AlertSeverity.INFO
            elif alert_type == "death_star":
                severity = AlertSeverity.WARNING

            self.alert_manager.send(
                title=f"Markdown Alert: {alert_type}",
                message=message,
                severity=severity,
                metadata={"warehouse": item.warehouse_number, "price": item.markdown_price}
            )

        # Send via FREE FOREVER API integrations (ntfy, Telegram, Discord)
        if self.use_api_integrations and self.api_manager:
            # Run async notification in sync context
            asyncio.create_task(self._send_api_notification(alert_type, item, message))

    async def _send_api_notification(self, alert_type: str, item: MarkdownItem, message: str):
        """Send notification via FREE FOREVER APIs"""
        try:
            # Determine priority based on alert type
            priority = "default"
            if alert_type == "deep_discount" and item.discount_percent >= 60:
                priority = "high"
            elif alert_type == "death_star":
                priority = "high"

            # Format title
            titles = {
                "deep_discount": f"DEAL: {item.discount_percent:.0f}% OFF",
                "death_star": "LAST CHANCE",
                "manager_special": "MANAGER SPECIAL",
                "amazon_cheaper": "AMAZON ALERT"
            }
            title = titles.get(alert_type, "COSTCO ALERT")

            # Send to ntfy (primary)
            await self.api_manager.notifications.send_ntfy(title, message, priority)

        except Exception as e:
            print(f"[API] Notification error: {e}")

    def _update_automation_state(self, item: MarkdownItem):
        """Update automation components"""
        if self.heartbeat:
            self.heartbeat.update_metadata(
                last_item=item.name,
                markdowns_found=self.state.markdowns_found,
                session_id=self.state.session_id
            )

        if self.state_manager:
            self.state_manager.checkpoint(
                total_markdowns_found=self.state.markdowns_found,
                last_successful_url=f"warehouse_{item.warehouse_number}"
            )

    async def run_simulation(self, num_items: int = 50) -> dict:
        """
        Run simulation with synthetic data and Amazon comparison.

        Args:
            num_items: Number of items to simulate

        Returns:
            Full report with markdowns and alerts
        """
        print(f"\n[v5] Running simulation with {num_items} items...")

        sample_products = [
            ("Samsung 65\" QLED TV", 1299.99),
            ("DeWalt 20V Drill Kit", 299.99),
            ("Sony Noise Canceling Headphones", 279.99),
            ("Vitamix Blender Pro", 449.99),
            ("HP LaserJet Printer", 399.99),
            ("Milwaukee Tool Set", 199.99),
            ("Kirkland Organic Coffee 2.5lb", 19.99),
            ("Callaway Golf Clubs Set", 599.99),
            ("Tempur-Pedic Pillow", 79.99),
            ("Nature Made Vitamin D3", 24.99),
        ]

        warehouses = list(self.geocoder.warehouses.keys())[:100]

        async with AmazonPriceChecker() as amazon_checker:
            for i in range(num_items):
                product = random.choice(sample_products)
                warehouse_num = int(random.choice(warehouses))

                # Generate markdown price
                original = product[1]
                code_type = random.choices(
                    [".97", ".00", ".88", ".99"],
                    weights=[40, 20, 15, 25]
                )[0]

                if code_type == ".97":
                    markdown = float(f"{int(original * random.uniform(0.5, 0.8))}.97")
                elif code_type == ".00":
                    markdown = float(f"{int(original * random.uniform(0.3, 0.6))}.00")
                elif code_type == ".88":
                    markdown = float(f"{int(original * random.uniform(0.4, 0.7))}.88")
                else:
                    markdown = original

                product_data = {
                    "product_id": f"SIM-{i:04d}",
                    "name": product[0],
                    "original_price": original,
                    "current_price": markdown,
                    "has_asterisk": random.random() < 0.15,
                    "tag_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
                }

                await self.process_with_amazon_comparison(product_data, warehouse_num, amazon_checker)

                self.state.items_processed += 1

                # Progress update
                if (i + 1) % 10 == 0:
                    print(f"  Processed {i + 1}/{num_items} items...")

        return self.generate_report()

    def generate_report(self) -> dict:
        """Generate comprehensive report"""
        report = {
            "meta": {
                "version": "v5_INTEGRATED",
                "session_id": self.state.session_id,
                "generated_at": datetime.now().isoformat(),
                "automation_enabled": self.use_automation,
                "amazon_comparison_enabled": bool(Config.CANOPY_API_KEY),
                "is_markdown_monday": self._is_markdown_monday()
            },
            "summary": {
                "total_processed": self.state.items_processed,
                "markdowns_found": len(self.discovered_markdowns),
                "alerts_generated": len(self.alerts_generated),
                "by_price_code": {},
                "by_category": {},
                "average_discount": 0.0,
                "amazon_comparisons": 0,
                "amazon_better_count": 0
            },
            "alerts": self.alerts_generated,
            "markdowns": [asdict(m) for m in self.discovered_markdowns]
        }

        # Calculate summaries
        if self.discovered_markdowns:
            discounts = [m.discount_percent for m in self.discovered_markdowns]
            report["summary"]["average_discount"] = round(sum(discounts) / len(discounts), 1)

            for m in self.discovered_markdowns:
                # By price code
                code = m.price_code
                report["summary"]["by_price_code"][code] = \
                    report["summary"]["by_price_code"].get(code, 0) + 1

                # By category
                cat = m.category
                report["summary"]["by_category"][cat] = \
                    report["summary"]["by_category"].get(cat, 0) + 1

                # Amazon stats
                if m.amazon and m.amazon.amazon_price:
                    report["summary"]["amazon_comparisons"] += 1
                    if not m.amazon.costco_is_better:
                        report["summary"]["amazon_better_count"] += 1

        return report

    def shutdown(self):
        """Graceful shutdown"""
        print("\n[v5] Shutting down...")

        if self.use_automation:
            if self.heartbeat:
                self.heartbeat.stop()
            if self.state_manager:
                self.state_manager.save()
            if self.logger:
                self.logger.info("Shutdown complete")

        # Close API integrations
        if self.use_api_integrations and self.api_manager:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.api_manager.close_all())
            except RuntimeError:
                # No running loop, create one for cleanup
                asyncio.run(self.api_manager.close_all())

        print("[v5] Shutdown complete")

    async def analyze_deal_with_llm(self, item: MarkdownItem) -> Optional[Dict]:
        """
        Analyze a deal using Groq LLM (FREE - 14,400 req/day).

        Returns analysis with deal quality score and reasoning.
        """
        if not self.use_api_integrations or not self.api_manager:
            return None

        return await self.api_manager.llm.analyze_deal(
            item.name,
            item.original_price,
            item.markdown_price,
            item.category
        )

    async def search_with_perplexity(self, query: str) -> Optional[str]:
        """
        Search using Perplexity API ($5/month free credit).

        Good for real-time price research and competitor analysis.
        """
        if not self.use_api_integrations or not self.api_manager:
            return None

        return await self.api_manager.llm.perplexity_search(query)

    async def enrich_product_data(self, barcode: str) -> Optional[Dict]:
        """
        Enrich product with data from Open Food Facts / Brocade.io (FREE).
        """
        if not self.use_api_integrations or not self.api_manager:
            return None

        return await self.api_manager.products.enrich_product(barcode)

    def export_json(self, data: dict, output_path: str):
        """Export report to JSON"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"[v5] Exported to {output_path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Warehouse Runner v5 INTEGRATED - Full Stack Markdown Hunter"
    )
    parser.add_argument("--simulate", action="store_true", help="Run simulation")
    parser.add_argument("--items", type=int, default=50, help="Items to simulate")
    parser.add_argument("--no-automation", action="store_true", help="Disable automation")
    parser.add_argument("--output", type=str, help="Output JSON path")
    parser.add_argument("--canopy-key", type=str, help="Canopy API key for Amazon comparison")

    args = parser.parse_args()

    # Set API key if provided
    if args.canopy_key:
        Config.CANOPY_API_KEY = args.canopy_key

    print("=" * 70)
    print("Warehouse Runner v5 INTEGRATED")
    print("Full Stack Markdown Hunter + FREE FOREVER APIs")
    print("=" * 70)
    print("Round Table Decision: Automation First (6-1 vote)")
    print("FREE API Round Table: Notifications First (6-0 unanimous)")
    print("Features:")
    print("  - Automation: Health monitoring, alerts, recovery")
    print("  - Amazon: Price comparison via Canopy API")
    print("  - Intelligence: Price codes, Markdown Monday, categories")
    print("  - Notifications: ntfy.sh, Telegram, Discord (FREE)")
    print("  - LLM Analysis: Groq (14,400/day), Perplexity ($5/mo)")
    print("  - Product Data: Open Food Facts, Brocade.io (FREE)")
    print("=" * 70)

    try:
        runner = WarehouseRunnerV5(use_automation=not args.no_automation)

        if args.simulate:
            report = asyncio.run(runner.run_simulation(num_items=args.items))

            print(f"\n{'=' * 70}")
            print("SIMULATION RESULTS")
            print('=' * 70)
            print(f"Items processed: {report['summary']['total_processed']}")
            print(f"Markdowns found: {report['summary']['markdowns_found']}")
            print(f"Alerts generated: {report['summary']['alerts_generated']}")
            print(f"Average discount: {report['summary']['average_discount']}%")

            if report['summary']['amazon_comparisons'] > 0:
                print(f"\nAmazon Comparisons:")
                print(f"  Compared: {report['summary']['amazon_comparisons']}")
                print(f"  Amazon better: {report['summary']['amazon_better_count']}")

            print(f"\nBy Price Code:")
            for code, count in report['summary']['by_price_code'].items():
                print(f"  {code}: {count}")

            if args.output:
                runner.export_json(report, args.output)
        else:
            print("\nUsage:")
            print("  --simulate          Run simulation")
            print("  --items N           Number of items")
            print("  --no-automation     Disable automation")
            print("  --output PATH       Export to JSON")
            print("  --canopy-key KEY    Canopy API key")
            print("\nExample:")
            print("  python warehouse_runner_v5_INTEGRATED.py --simulate --items 100")

        runner.shutdown()
        print("\n" + "=" * 70)
        print("v5 INTEGRATED: Mission Complete")
        print("=" * 70)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
