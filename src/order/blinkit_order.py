from playwright.async_api import Page


class BlinkitOrder:
    def __init__(self, page: Page):
        self.page = page

    async def search_product(self, product_name: str):
        """Searches for a product using the search bar."""
        print(f"Searching for item: {product_name}...")
        try:
            # 1. Activate Search
            if await self.page.is_visible("a[href='/s/']"):
                await self.page.click("a[href='/s/']")
            elif await self.page.is_visible(
                "div[class*='SearchBar__PlaceholderContainer']"
            ):
                await self.page.click("div[class*='SearchBar__PlaceholderContainer']")
            else:
                # Fallback: type directly if input is visible, or click generic search text
                if await self.page.is_visible("input[placeholder*='Search']"):
                    await self.page.click("input[placeholder*='Search']")
                else:
                    await self.page.click("text='Search'", timeout=3000)

            # 2. Type and Submit
            search_input = await self.page.wait_for_selector(
                "input[placeholder*='Search'], input[type='text']",
                state="visible",
                timeout=5000,
            )
            await search_input.fill(product_name)
            await self.page.keyboard.press("Enter")

            # 3. Wait for results
            print("Waiting for results...")
            try:
                # Wait for product cards
                await self.page.wait_for_selector(
                    "div[role='button']:has-text('ADD')", timeout=10000
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

    async def set_location(self, location_name: str):
        """Sets the location manually."""
        print(f"Setting location to: {location_name}...")
        try:
            # Check if the modal is open, if not try to open it
            if not await self.page.is_visible("input[name='select-locality']"):
                # Click location bar
                if await self.page.is_visible("div[class*='LocationBar__Container']"):
                    await self.page.click("div[class*='LocationBar__Container']")

            # Wait for input
            location_input = await self.page.wait_for_selector(
                "input[name='select-locality'], input[placeholder*='search delivery location']",
                state="visible",
                timeout=5000,
            )

            await location_input.fill(location_name)
            await self.page.wait_for_timeout(1000)

            # Select first result
            first_result = self.page.locator(
                "div[class*='LocationSearchBox__LocationItemContainer']"
            ).first
            if await first_result.is_visible():
                await first_result.click()
                print("Selected first location result.")

                # Wait for location update
                await self.page.wait_for_timeout(2000)

                # Check if this new location is unavailable
                if await self.page.is_visible("text=Currently unavailable"):
                    print(
                        "WARNING: Store is marked as 'Currently unavailable' at this new location."
                    )
            else:
                print("No location results found.")

        except Exception as e:
            print(f"Error setting location: {e}")

    async def get_search_results(self, limit=5):
        """Parses search results and returns a list of product details."""
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

                # Extract Name
                name_locator = card.locator("div[class*='line-clamp-2']")
                if await name_locator.count() > 0:
                    name = await name_locator.first.inner_text()
                else:
                    lines = [line for line in text_content.split("\n") if line.strip()]
                    name = lines[0] if lines else "Unknown Product"

                # Extract Price
                price = "Unknown Price"
                if "₹" in text_content:
                    for part in text_content.split("\n"):
                        if "₹" in part:
                            price = part.strip()
                            break

                results.append({"index": i, "name": name, "price": price})

        except Exception as e:
            print(f"Error extracting search results: {e}")

        return results

    async def add_to_cart(self, item_index: int = 0):
        """Adds the Nth item from search results to the cart."""
        print(f"Adding item at index {item_index} to cart...")
        try:
            cards = (
                self.page.locator("div[role='button']")
                .filter(has_text="ADD")
                .filter(has_text="₹")
            )

            count = await cards.count()
            if count <= item_index:
                print(f"Item index {item_index} out of range (found {count} items).")
                return

            card = cards.nth(item_index)

            # Find the ADD button specifically inside the card
            add_btn = card.locator("div").filter(has_text="ADD").last

            if await add_btn.is_visible():
                await add_btn.click()
                print("Clicked ADD button.")
            else:
                # Check for checkmark/counter indicating already added
                if await card.locator("text='+'").is_visible():
                    print("Item already in cart. Incrementing...")
                    await card.locator("text='+'").click()
                else:
                    print("Could not find ADD button or increment controls.")

            await self.page.wait_for_timeout(1000)

            # Check for "Store Unavailable" modal
            if await self.page.is_visible(
                "div:has-text('Sorry, can\\'t take your order')"
            ):
                print("WARNING: Store is unavailable (Modal detected).")
                return

        except Exception as e:
            print(f"Error adding to cart: {e}")

    async def get_saved_addresses(self):
        """Scrapes saved addresses from the selection modal."""
        print("Checking for address selection modal...")
        try:
            if not await self.page.is_visible("text='Select delivery address'"):
                print("Address selection modal not visible.")
                return []

            print("Address modal detected. Parsing addresses...")
            address_items = self.page.locator(
                "div[class*='AddressList__AddressItemWrapper']"
            )
            count = await address_items.count()

            addresses = []
            for i in range(count):
                item = address_items.nth(i)
                # Parse label
                label_el = item.locator("div[class*='AddressList__AddressLabel']")
                if await label_el.count() > 0:
                    label = await label_el.inner_text()
                else:
                    label = "Unknown"

                # Parse details
                details_el = item.locator(
                    "div[class*='AddressList__AddressDetails']"
                ).last
                if await details_el.count() > 0:
                    details = await details_el.inner_text()
                else:
                    details = ""

                addresses.append({"index": i, "label": label, "details": details})
            return addresses

        except Exception as e:
            print(f"Error getting addresses: {e}")
            return []

    async def select_address(self, index: int):
        """Selects an address by index."""
        try:
            items = self.page.locator("div[class*='AddressList__AddressItemWrapper']")
            if index < await items.count():
                print(f"Selecting address at index {index}...")
                await items.nth(index).click()
                # Wait for modal to close or location to update
                await self.page.wait_for_timeout(2000)
            else:
                print(f"Invalid address index: {index}")
        except Exception as e:
            print(f"Error selecting address: {e}")

    async def get_cart_items(self):
        """Checks items in the cart and returns the text content."""
        print("Checking cart...")
        try:
            cart_btn = self.page.locator(
                "div[class*='CartButton__Button'], div[class*='CartButton__Container']"
            )

            if await cart_btn.count() > 0:
                await cart_btn.first.click()
                print("Clicked My Cart.")

                # Verify opening
                try:
                    # Wait briefly for drawer or modals
                    await self.page.wait_for_timeout(2000)

                    # 1. Critical Availability Check
                    if (
                        await self.page.is_visible("text=Sorry, can't take your order")
                        or await self.page.is_visible("text=Currently unavailable")
                        or await self.page.is_visible("text=High Demand")
                    ):
                        return "CRITICAL: Store is unavailable. 'Sorry, can't take your order'. Please try again later."

                    # 2. Check for Bill Details or Proceed Button (indicators of a valid active cart)
                    # If these are NOT present, we shouldn't claim the cart is functioning.
                    is_cart_active = (
                        await self.page.is_visible("text=/Bill details/i")
                        or await self.page.is_visible("button:has-text('Proceed')")
                        or await self.page.is_visible("text=ordering for")
                    )

                    # Scrape content
                    drawer = self.page.locator(
                        "div[class*='CartDrawer'], div[class*='CartSidebar']"
                    ).first

                    if await drawer.count() > 0:
                        content = await drawer.inner_text()
                        # Double check availability in content text
                        if (
                            "Currently unavailable" in content
                            or "can't take your order" in content
                        ):
                            return "CRITICAL: Store is unavailable (Text detected in cart). Please try again later."
                        return content

                    if is_cart_active:
                        return "Cart is open. (Could not scrape specific drawer content, but functionality is active)."
                    else:
                        return "WARNING: Cart opened but seems empty or store is unavailable (No bill details/proceed button found)."

                except Exception as e:
                    return f"Cart drawer checking timed out or error: {e}"
            else:
                return "Cart button not found."

        except Exception as e:
            return f"Error getting cart items: {e}"

    async def place_order(self):
        """Proceeds to checkout."""
        print("Proceeding to Place Order...")
        try:
            proceed_btn = (
                self.page.locator("button, div").filter(has_text="Proceed").last
            )

            # If Proceed not visible, try opening the cart first
            if not await proceed_btn.is_visible():
                print("Proceed button not visible. Attempting to open Cart drawer...")
                cart_btn = self.page.locator(
                    "div[class*='CartButton__Button'], div[class*='CartButton__Container']"
                )
                if await cart_btn.count() > 0:
                    await cart_btn.first.click()
                    print("Clicked 'My Cart' button.")
                    await self.page.wait_for_timeout(2000)
                else:
                    print("Could not find 'My Cart' button.")

            # Try clicking Proceed again
            if await proceed_btn.is_visible():
                await proceed_btn.click()
                print("Clicked Proceed.")
                await self.page.wait_for_timeout(3000)
            else:
                print(
                    "Proceed button not visible. Cart might be empty or Store Unavailable."
                )

        except Exception as e:
            print(f"Error placing order: {e}")
