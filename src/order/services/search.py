import urllib.parse

from .base import BaseService


class SearchService(BaseService):
    async def _dismiss_overlays(self):
        """Dismiss any popups, modals, or overlays that may block interaction."""
        try:
            # Close any visible close/dismiss buttons
            for selector in [
                "button[aria-label='close']",
                "div[class*='Modal'] button",
                "div[class*='Overlay'] button",
                "button:has-text('✕')",
                "button:has-text('×')",
            ]:
                if await self.page.is_visible(selector):
                    await self.page.click(selector, timeout=2000)
                    await self.page.wait_for_timeout(300)
        except Exception:
            pass

    async def _try_click_search(self) -> bool:
        """Try to activate the search bar via click. Returns True if successful."""
        selectors = [
            "a[href='/s/']",
            "div[class*='SearchBar__PlaceholderContainer']",
            "input[placeholder*='Search']",
            "text='Search'",
        ]
        for selector in selectors:
            try:
                if await self.page.is_visible(selector):
                    await self.page.click(selector, timeout=5000)
                    return True
            except Exception:
                continue
        return False

    async def search_product(self, product_name: str):
        """Searches for a product using the search bar."""
        print(f"Searching for item: {product_name}...")
        if self.manager:
            self.manager.current_query = (
                product_name  # Store current query for state tracking
            )

        try:
            # Dismiss any overlays that might block the search bar
            await self._dismiss_overlays()

            # Strategy 1: Try clicking the search bar and typing
            search_succeeded = False
            try:
                if await self._try_click_search():
                    search_input = await self.page.wait_for_selector(
                        "input[placeholder*='Search'], input[type='text']",
                        state="visible",
                        timeout=5000,
                    )
                    # Triple-click to select all existing text, then fill
                    await search_input.click(click_count=3)
                    await search_input.fill(product_name)
                    await self.page.keyboard.press("Enter")
                    search_succeeded = True
            except Exception as e:
                print(f"Search bar click/type failed: {e}. Falling back to URL navigation.")

            # Strategy 2: Fallback — navigate directly to search URL
            if not search_succeeded:
                encoded_query = urllib.parse.quote(product_name)
                search_url = f"https://blinkit.com/s/?q={encoded_query}"
                print(f"Navigating directly to search URL: {search_url}")
                await self.page.goto(search_url, wait_until="domcontentloaded")

            # Wait for results
            print("Waiting for results...")
            try:
                await self.page.wait_for_selector(
                    "div[role='button']:has-text('ADD')", timeout=30000
                )
                print("Search results loaded.")
            except Exception:
                print(
                    "Timed out waiting for product cards. Checking for 'No results'..."
                )
                if await self.page.is_visible("text='No results found'"):
                    print("No results found for this query.")
                else:
                    print("Could not detect standard product cards.")

        except Exception as e:
            print(f"Error during search: {e}")

    async def get_search_results(self, limit=20):
        """Parses search results and returns a list of product details including IDs."""
        results = []
        try:
            cards = (
                self.page.locator("div[role='button']")
                .filter(has_text="ADD")
                .filter(has_text="₹")
            )

            count = await cards.count()
            print(f"Found {count} product cards.")

            for i in range(min(count, limit)):
                card = cards.nth(i)
                text_content = await card.inner_text()

                # Extract ID
                product_id = await card.get_attribute("id")
                if not product_id:
                    product_id = "unknown"

                # Extract Name
                name_locator = card.locator("div[class*='line-clamp-2']")
                if await name_locator.count() > 0:
                    name = await name_locator.first.inner_text()
                else:
                    lines = [line for line in text_content.split("\n") if line.strip()]
                    name = lines[0] if lines else "Unknown Product"

                # Store in known products including the source query
                if product_id != "unknown" and self.manager:
                    self.manager.known_products[product_id] = {
                        "source_query": self.manager.current_query,
                        "name": name,
                    }

                # Extract Price
                price = "Unknown Price"
                if "₹" in text_content:
                    for part in text_content.split("\n"):
                        if "₹" in part:
                            price = part.strip()
                            break

                results.append(
                    {"index": i, "id": product_id, "name": name, "price": price}
                )

        except Exception as e:
            print(f"Error extracting search results: {e}")

        return results

    async def check_product_availability_at_location(
        self, product_name: str, location_name: str
    ):
        """
        Check if a product is available at a specific location.
        Returns availability status including store status and product availability.
        """
        print(f"Checking availability of '{product_name}' at '{location_name}'...")
        result = {
            "location": location_name,
            "available": False,
            "store_status": "unknown",
            "products_found": [],
            "error": None,
        }

        try:
            # Import location service to change location
            if not self.manager:
                result["error"] = "Manager not available"
                return result

            # Set location
            await self.manager.location_service.set_location(location_name)
            await self.page.wait_for_timeout(2000)

            # Check for store availability messages
            if await self.page.is_visible("text=Currently unavailable"):
                result["store_status"] = "unavailable"
                print(f"Store is currently unavailable at {location_name}")
                return result

            if await self.page.is_visible("text=Store is closed"):
                result["store_status"] = "closed"
                print(f"Store is closed at {location_name}")
                return result

            result["store_status"] = "open"

            # Search for the product
            await self.search_product(product_name)
            await self.page.wait_for_timeout(1500)

            # Get search results
            products = await self.get_search_results(limit=5)

            if products:
                result["available"] = True
                result["products_found"] = products
                print(f"Found {len(products)} products at {location_name}")
            else:
                print(f"No products found at {location_name}")

        except Exception as e:
            result["error"] = str(e)
            print(f"Error checking availability at {location_name}: {e}")

        return result
