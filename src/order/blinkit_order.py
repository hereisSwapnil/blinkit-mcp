from playwright.async_api import Page
from .services.search import SearchService
from .services.location import LocationService
from .services.cart import CartService
from .services.checkout import CheckoutService
from typing import List


class BlinkitOrder:
    def __init__(self, page: Page):
        self.page = page

        # State tracking for cross-search cart addition
        self.known_products = {}  # Maps product_id -> {'source_query': str, 'name': str}
        self.current_query = None

        # Initialize Services
        self.search_service = SearchService(page, self)
        self.location_service = LocationService(page, self)
        self.cart_service = CartService(page, self)
        self.checkout_service = CheckoutService(page, self)

        # Attach blocking listener for debugging specific relevant errors
        self.page.on("response", self._handle_response)

    async def _handle_response(self, response):
        """Monitor network responses for payment failures."""
        try:
            url = response.url
            if "zpaykit" in url or "payment" in url:
                if response.status >= 400:
                    print(f"DEBUG: Payment API Error {response.status} at {url}")

                # Try to parse JSON for failure messages even on 200 OK
                if "application/json" in response.headers.get("content-type", ""):
                    try:
                        data = await response.json()
                        if isinstance(data, dict) and (
                            data.get("status") == "failed" or data.get("error")
                        ):
                            print(f"DEBUG: Payment API Failure captured: {data}")
                    except Exception:
                        pass
        except Exception:
            pass

    # --- Search Delegate ---
    async def search_product(self, product_name: str):
        return await self.search_service.search_product(product_name)

    async def get_search_results(self, limit=10):
        return await self.search_service.get_search_results(limit)

    async def check_product_availability(
        self, product_name: str, locations: List[str]
    ):
        """
        Check product availability across multiple locations.
        Returns a list of availability results for each location.
        """
        results = []
        for location in locations:
            result = (
                await self.search_service.check_product_availability_at_location(
                    product_name, location
                )
            )
            results.append(result)
        return results

    # --- Location Delegate ---
    async def set_location(self, location_name: str):
        return await self.location_service.set_location(location_name)

    async def get_saved_addresses(self):
        return await self.location_service.get_saved_addresses()

    async def select_address(self, index: int):
        return await self.location_service.select_address(index)

    # --- Cart Delegate ---
    async def add_to_cart(self, product_id: str, quantity: int = 1):
        return await self.cart_service.add_to_cart(product_id, quantity)

    async def remove_from_cart(self, product_id: str, quantity: int = 1):
        return await self.cart_service.remove_from_cart(product_id, quantity)

    async def get_cart_items(self):
        return await self.cart_service.get_cart_items()

    # --- Checkout Delegate ---
    async def place_order(self):
        return await self.checkout_service.place_order()

    async def select_payment_method(self):
        return await self.checkout_service.select_payment_method()

    async def click_pay_now(self):
        return await self.checkout_service.click_pay_now()
