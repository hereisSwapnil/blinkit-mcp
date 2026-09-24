from .base import BaseService


class CartService(BaseService):
    async def _dismiss_overlays(self):
        """Dismiss any popups, modals, or overlays that may block interaction."""
        try:
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

    async def _safe_click(self, locator, description="element", timeout=10000):
        """Click an element with fallback strategies: scroll into view, force click, JS click."""
        try:
            # First, scroll the element into view
            await locator.scroll_into_view_if_needed(timeout=5000)
            await self.page.wait_for_timeout(300)
        except Exception:
            pass

        # Attempt 1: Normal click
        try:
            await locator.click(timeout=timeout)
            return True
        except Exception as e:
            print(f"Normal click failed on {description}: {e}")

        # Attempt 2: Force click (bypasses actionability checks)
        try:
            await locator.click(force=True, timeout=5000)
            print(f"Force click succeeded on {description}.")
            return True
        except Exception as e:
            print(f"Force click failed on {description}: {e}")

        # Attempt 3: JavaScript click (last resort)
        try:
            await locator.evaluate("el => el.click()")
            print(f"JS click succeeded on {description}.")
            return True
        except Exception as e:
            print(f"JS click failed on {description}: {e}")

        return False

    async def add_to_cart(self, product_id: str, quantity: int = 1):
        """Adds a product to the cart by its unique ID. Supports multiple quantities."""
        print(f"Adding product with ID {product_id} to cart (Quantity: {quantity})...")
        try:
            # Dismiss any overlays that might block buttons
            await self._dismiss_overlays()

            # Target the specific card by ID
            card = self.page.locator(f"div[id='{product_id}']")

            if await card.count() == 0:
                print(f"Product ID {product_id} not found on current page.")

                # Check if we know this product from a previous search
                if self.manager and product_id in self.manager.known_products:
                    print("Product found in history.")
                    product_info = self.manager.known_products[product_id]
                    source_query = product_info.get("source_query")

                    if source_query:
                        print(
                            f"Navigating back to search results for '{source_query}'..."
                        )
                        # Delegate search back to manager/search service
                        if hasattr(self.manager, "search_product"):
                            await self.manager.search_product(source_query)

                        # Re-locate the card after search
                        card = self.page.locator(f"div[id='{product_id}']")
                        if await card.count() == 0:
                            print(
                                f"CRITICAL: Product {product_id} still not found after re-search."
                            )
                            return
                    else:
                        print("No source query found for this product.")
                        return
                else:
                    print("Product ID unknown and not on current page.")
                    return

            # Dismiss overlays again after potential re-search
            await self._dismiss_overlays()

            # Find the ADD button specifically inside the card
            add_btn = card.locator("div").filter(has_text="ADD").last

            items_to_add = quantity

            # If ADD button is visible, click it once to start
            if await add_btn.is_visible():
                clicked = await self._safe_click(
                    add_btn, f"ADD button for {product_id}"
                )
                if clicked:
                    print(f"Clicked ADD button for {product_id} (1/{quantity}).")
                    items_to_add -= 1
                    # Wait for the counter to appear
                    await self.page.wait_for_timeout(500)
                else:
                    print(f"Failed to click ADD button for {product_id}.")
                    return

            # Use increment button for remaining quantity
            if items_to_add > 0:
                # Wait for the counter to initialize
                await self.page.wait_for_timeout(1000)

                # Try multiple selectors — .icon-plus is stale in current Blinkit DOM
                plus_btn = card.locator(
                    "[class*='increment' i], [class*='Increment'], "
                    "[class*='plus' i], [class*='Plus'], "
                    "[aria-label*='increase' i], [aria-label*='increment' i]"
                ).first
                if await plus_btn.count() == 0:
                    plus_btn = card.locator(".icon-plus").first
                if await plus_btn.count() > 0:
                    plus_btn = plus_btn.locator("..")
                if await plus_btn.count() == 0:
                    plus_btn = card.locator("div, button").filter(has_text="+").last

                if await plus_btn.is_visible():
                    for i in range(items_to_add):
                        await self._safe_click(plus_btn, f"+ button for {product_id}")
                        print(
                            f"Incrementing quantity for {product_id} ({quantity - items_to_add + i + 1}/{quantity})."
                        )
                        # Check for limit reached
                        try:
                            limit_msg = self.page.get_by_text(
                                "Sorry, you can't add more of this item"
                            )
                            if await limit_msg.is_visible(timeout=1000):
                                print(f"Quantity limit reached for {product_id}.")
                                break
                        except Exception:
                            pass

                        await self.page.wait_for_timeout(500)
                else:
                    print(
                        f"Could not find '+' button to add remaining quantity for {product_id}."
                    )

            await self.page.wait_for_timeout(1000)

            # Check for "Store Unavailable" modal
            if await self.page.is_visible(
                "div:has-text('Sorry, can\\'t take your order')"
            ):
                print("WARNING: Store is unavailable (Modal detected).")
                return

        except Exception as e:
            print(f"Error adding to cart: {e}")

    async def remove_from_cart(self, product_id: str, quantity: int = 1):
        """Removes a specific quantity of a product from the cart."""
        print(f"Removing {quantity} of product ID {product_id} from cart...")
        try:
            # Dismiss any overlays
            await self._dismiss_overlays()

            # Target the specific card by ID
            card = self.page.locator(f"div[id='{product_id}']")

            if await card.count() == 0:
                # Attempt recovery via search if known
                if self.manager and product_id in self.manager.known_products:
                    product_info = self.manager.known_products[product_id]
                    source_query = product_info.get("source_query")
                    if source_query:
                        if hasattr(self.manager, "search_product"):
                            await self.manager.search_product(source_query)
                        card = self.page.locator(f"div[id='{product_id}']")
                        if await card.count() == 0:
                            print(
                                f"Product {product_id} not found after recovery search."
                            )
                            return
                else:
                    print(f"Product ID {product_id} not found and unknown.")
                    return

            # Check for decrement button
            minus_btn = card.locator(".icon-minus").first
            if await minus_btn.count() > 0:
                minus_btn = minus_btn.locator("..")
            else:
                minus_btn = card.locator("text='-'").first

            if await minus_btn.is_visible():
                for i in range(quantity):
                    await self._safe_click(minus_btn, f"- button for {product_id}")
                    print(
                        f"Decrementing quantity for {product_id} ({i + 1}/{quantity})."
                    )
                    await self.page.wait_for_timeout(500)

                    # If ADD button reappears, item is fully removed
                    if (
                        await card.locator("div")
                        .filter(has_text="ADD")
                        .last.is_visible()
                    ):
                        print(f"Item {product_id} completely removed from cart.")
                        break
            else:
                print(f"Item {product_id} is not in cart (no '-' button found).")

        except Exception as e:
            print(f"Error removing from cart: {e}")

    async def get_cart_items(self):
        """Checks items in the cart and returns the text content."""
        try:
            # Dismiss any overlays before trying to open the cart
            await self._dismiss_overlays()

            drawer = self.page.locator(
                "div[class*='CartDrawer'], div[class*='CartSidebar'], div.cart-modal-rn, div[class*='CartWrapper__CartContainer']"
            ).first

            # If drawer isn't visible, try to click the cart button to open it
            if not await drawer.is_visible():
                cart_btn = (
                    self.page.locator(
                        "div[class*='CartButton__Button'], div[class*='CartButton__Container'], a[href='/cart'], div[class*='cart']"
                    )
                    .filter(has_text="Cart")
                    .last
                )

                if await cart_btn.count() == 0:
                    cart_btn = self.page.locator("div[class*='CartButton']").first

                if await cart_btn.count() > 0:
                    clicked = await self._safe_click(cart_btn, "cart button")
                    if not clicked:
                        return (
                            "Failed to click cart button (may be blocked by overlay)."
                        )
                    await self.page.wait_for_timeout(2000)
                else:
                    # Look for anything with Cart or View Cart
                    alt_btn = (
                        self.page.locator("button, div").filter(has_text="Cart").last
                    )
                    if await alt_btn.count() > 0:
                        await self._safe_click(alt_btn, "alt cart button")
                        await self.page.wait_for_timeout(2000)
                    else:
                        return "Cart button not found."

            if not await drawer.is_visible():
                return "Cart drawer did not open."

            # Verify availability
            if (
                await self.page.is_visible("text=Sorry, can't take your order")
                or await self.page.is_visible("text=Currently unavailable")
                or await self.page.is_visible("text=High Demand")
            ):
                return "CRITICAL: Store is unavailable. 'Sorry, can't take your order'. Please try again later."

            if await self._is_store_closed():
                return "CRITICAL: Store is closed."

            # Scrape content more cleanly using evaluate to extract meaningful parts
            content = await drawer.evaluate("""(drawer) => {
                let text = drawer.innerText;
                let results = ["--- CART DETAILS ---"];
                
                // Try to extract items
                let items = drawer.querySelectorAll("div[class*='DefaultProductCard__Container'], div[class*='CartProduct__Container']");
                items.forEach(item => {
                    let title = item.querySelector("div[class*='ProductTitle']")?.innerText || "";
                    let variant = item.querySelector("div[class*='ProductVariant']")?.innerText || "";
                    let price = item.querySelector("div[class*='Price-']")?.innerText || "";
                    let qtyElement = item.querySelector("div[class*='AddToCart___StyledDiv']")?.parentElement;
                    let qty = qtyElement ? qtyElement.innerText.replace(/\\n/g, '').replace("-", "").replace("+", "").trim() : "1";
                    if (title) {
                        results.push(`• ${title} | ${variant} | ${price} | Qty: ${qty}`);
                    }
                });
                
                if (items.length === 0) {
                    results.push("Raw text: " + text.substring(0, 300) + "...");
                }
                
                // Try to extract Bill Details
                let billItems = drawer.querySelectorAll("div[class*='BillCard__BillItemContainer']");
                if (billItems.length > 0) results.push("\\n--- BILL DETAILS ---");
                billItems.forEach(item => {
                    let textParts = item.innerText.split('\\n').map(t => t.trim()).filter(t => t);
                    if (textParts.length >= 2) {
                        results.push(`${textParts[0]}: ${textParts[textParts.length-1]}`);
                    }
                });
                
                // Get Delivery Address
                let addressHeading = drawer.querySelector("div[class*='ListStrip__Heading']")?.innerText || "";
                let addressSub = drawer.querySelector("div[class*='ListStrip__SubHeading']")?.innerText || "";
                if (addressHeading) {
                    results.push("\\n--- DELIVERY TO ---");
                    results.push(`${addressHeading} - ${addressSub}`);
                }
                
                // Get Total
                let totalText = drawer.querySelector("div[class*='CheckoutStrip__TotalText']")?.innerText || "";
                let finalPrice = drawer.querySelector("div[class*='CheckoutStrip__NetPriceText']")?.innerText || "";
                if (finalPrice) {
                    results.push(`\\n--- TOTAL TO PAY: ${finalPrice} ---`);
                }
                
                return results.join('\\n');
            }""")

            if "Currently unavailable" in content or "can't take your order" in content:
                return (
                    "CRITICAL: Store is unavailable. Please try again later.\\n"
                    + content
                )

            return content

        except Exception as e:
            return f"Error getting cart items: {e}"
