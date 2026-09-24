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

                # Extract image URL
                image_url = ""
                img_locator = card.locator("img")
                if await img_locator.count() > 0:
                    src = await img_locator.first.get_attribute("src")
                    if src and src.startswith("http"):
                        image_url = src

                results.append(
                    {"index": i, "id": product_id, "name": name, "price": price, "image_url": image_url}
                )

        except Exception as e:
            print(f"Error extracting search results: {e}")

        return results
