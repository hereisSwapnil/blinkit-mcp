from .base import BaseService


class CheckoutService(BaseService):
    async def place_order(self):
        """Proceeds to checkout."""

        if await self._is_store_closed():
            return "CRITICAL: Store is closed."

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
                print(
                    "Cart checkout successfully.\nYou can select the payment method and proceed to pay."
                )
                await self.page.wait_for_timeout(3000)
            else:
                print(
                    "Proceed button not visible. Cart might be empty or Store Unavailable."
                )

        except Exception as e:
            print(f"Error placing order: {e}")

    async def get_upi_ids(self):
        """Scrapes available UPI IDs/options from the payment widget."""
        print("Getting available UPI IDs...")
        try:
            iframe_element = await self.page.wait_for_selector(
                "#payment_widget", timeout=30000
            )
            if not iframe_element:
                print("Payment widget iframe not found.")
                return []

            frame = await iframe_element.content_frame()
            if not frame:
                return []

            await frame.wait_for_load_state("networkidle")

            ids = []
            # Try to find elements that look like VPAs (contain @) inside the frame
            vpa_locators = frame.locator("text=/@/")
            count = await vpa_locators.count()
            for i in range(count):
                text = await vpa_locators.nth(i).inner_text()
                if "@" in text:
                    ids.append(text.strip())

            # Also add "Add new UPI ID" option if exists
            if await frame.locator("text='Add new UPI ID'").count() > 0:
                ids.append("Add new UPI ID")

            print(f"Found UPI IDs: {ids}")
            return ids

        except Exception as e:
            print(f"Error getting UPI IDs: {e}")
            return []

    async def select_upi_id(self, upi_id: str):
        """Selects a specific UPI ID or enters a new one."""
        print(f"Selecting UPI ID: {upi_id}...")
        try:
            iframe_element = await self.page.wait_for_selector(
                "#payment_widget", timeout=30000
            )
            if not iframe_element:
                return

            frame = await iframe_element.content_frame()
            if not frame:
                return

            # 1. Try to click on an existing saved VPA if it matches
            saved_vpa = frame.locator(f"text='{upi_id}'")
            if await saved_vpa.count() > 0:
                await saved_vpa.first.click()
                print(f"Clicked saved VPA: {upi_id}")
                return

            # 2. If not found, Select "UPI" / "Add new UPI ID" section
            # Click generic UPI header first if needed to expand
            upi_header = frame.locator("div").filter(has_text="UPI").last
            if await upi_header.count() > 0:
                await upi_header.click()

            await self.page.wait_for_timeout(500)

            # 3. Enter VPA in input
            input_locator = frame.locator(
                "input[placeholder*='UPI'], input[type='text']"
            )
            if await input_locator.count() > 0:
                await input_locator.first.fill(upi_id)
                print(f"Filled UPI ID: {upi_id}")

                # Verify
                verify_btn = frame.locator("text=Verify")
                if await verify_btn.count() > 0:
                    await verify_btn.click()
                    print("Clicked Verify button.")
            else:
                print("Could not find UPI input field.")

        except Exception as e:
            print(f"Error selecting UPI ID: {e}")

    async def click_pay_now(self):
        """Clicks the final Pay Now button."""
        print("Attempting to click Pay Now...")
        try:
            # Strategy 1: Specific class partial match
            pay_btn_specific = self.page.locator(
                "div[class*='Zpayments__Button']:has-text('Pay Now')"
            )
            if (
                await pay_btn_specific.count() > 0
                and await pay_btn_specific.first.is_visible()
            ):
                await pay_btn_specific.first.click()
                print("Clicked 'Pay Now' (specific class selector).")
                return

            # Strategy 2: Text match on page
            pay_btn_text = (
                self.page.locator("div, button").filter(has_text="Pay Now").last
            )
            if await pay_btn_text.count() > 0 and await pay_btn_text.is_visible():
                await pay_btn_text.click()
                print("Clicked 'Pay Now' (text selector).")
                return

            # Strategy 3: Check inside iframe
            iframe_element = await self.page.query_selector("#payment_widget")
            if iframe_element:
                frame = await iframe_element.content_frame()
                if frame:
                    frame_btn = frame.locator("text='Pay Now'")
                    if await frame_btn.count() > 0:
                        await frame_btn.first.click()
                        print("Clicked 'Pay Now' inside iframe.")
                        return

            print("Could not find 'Pay Now' button (timeout or not in DOM).")

        except Exception as e:
            print(f"Error clicking Pay Now: {e}")
