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

    async def select_payment_method(self):
        """Checks for Cash availability, selects it if available, else falls back to UPI QR."""
        print("Selecting payment method (Cash or UPI QR)...")
        try:
            iframe_element = await self.page.wait_for_selector(
                "#payment_widget", timeout=30000
            )
            if not iframe_element:
                print("Payment widget iframe not found.")
                return "Payment widget not found."

            frame = await iframe_element.content_frame()
            if not frame:
                return "Payment widget frame content not found."

            await frame.wait_for_load_state("networkidle")

            # Check Cash
            cash_panel = frame.locator("div[title='Cash']")
            if await cash_panel.count() > 0:
                # Check if it has a disabled attribute on the panel itself
                is_disabled_attr = (
                    await cash_panel.first.get_attribute("disabled") is not None
                )

                # Check aria-disabled on the inner button
                cash_button = cash_panel.locator("div[role='button']")
                is_aria_disabled = False
                if await cash_button.count() > 0:
                    is_aria_disabled = (
                        await cash_button.first.get_attribute("aria-disabled") == "true"
                    )

                if not is_disabled_attr and not is_aria_disabled:
                    print("Cash is available. Selecting Cash on Delivery...")
                    if await cash_button.count() > 0:
                        await cash_button.first.click()
                    else:
                        await cash_panel.first.click()
                    return "Selected Cash on Delivery. Call pay_now to finalize."
                else:
                    print("Cash is unavailable or disabled.")
            else:
                print("Cash option not found.")

            # If Cash is disabled or doesn't exist, try UPI -> Generate QR
            print("Selecting UPI and generating QR code...")
            upi_panel = frame.locator("div[title='UPI']")
            if await upi_panel.count() > 0:
                upi_button = upi_panel.locator("div[role='button']")
                if await upi_button.count() > 0:
                    # Check if already open
                    is_open = (
                        await upi_button.first.get_attribute("aria-expanded") == "true"
                    )
                    if not is_open:
                        await upi_button.first.click()
                        print("Clicked UPI.")
                else:
                    await upi_panel.first.click()

                await self.page.wait_for_timeout(1000)

                # Click Generate QR
                generate_qr_btn = frame.locator("button:has-text('Generate QR')")
                if await generate_qr_btn.count() > 0:
                    await generate_qr_btn.first.click()
                    print("Generated QR code. Please show the QR code to the customer.")
                    await self.page.wait_for_timeout(2000)  # Wait for QR to load

                    try:
                        qr_img_locator = frame.locator(
                            "div[class*='QrImageWrapper'] img"
                        )
                        await qr_img_locator.wait_for(state="visible", timeout=5000)
                        qr_src = await qr_img_locator.first.get_attribute("src")
                        if qr_src and qr_src.startswith("data:image/"):
                            base64_data = qr_src.split(",")[1]
                            return {
                                "status": "UPI QR Code generated successfully. Show it to the customer.",
                                "qr_base64": base64_data,
                                "format": qr_src.split(";")[0].split("/")[1],
                            }
                    except Exception as qr_e:
                        print(f"Failed to extract QR Code image: {qr_e}")

                    return (
                        "UPI QR Code generated successfully. Show it to the customer."
                    )
                else:
                    print("Generate QR button not found within UPI.")
                    return "UPI section opened but 'Generate QR' button not found."
            else:
                print("UPI option not found.")
                return "UPI option not found in payment widget."

        except Exception as e:
            print(f"Error selecting payment method: {e}")
            return f"Error: {str(e)}"

    async def click_pay_now(self):
        """Clicks the final Pay Now button."""
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
                print("Clicked 'Pay Now'. Please approve the payment on your UPI app.")
                return "Clicked Pay Now."

            # Strategy 2: Text match on page — covers both UPI "Pay Now" and COD "Place Order"
            import re as _re
            pay_btn_text = (
                self.page.locator("div, button")
                .filter(has_text=_re.compile(r"Pay Now|Place Order|Confirm Order", _re.IGNORECASE))
                .last
            )
            if await pay_btn_text.count() > 0 and await pay_btn_text.is_visible():
                await pay_btn_text.click()
                print("Clicked payment/order button.")
                return "Clicked Pay Now."

            # Strategy 3: Check inside iframe
            iframe_element = await self.page.query_selector("#payment_widget")
            if iframe_element:
                frame = await iframe_element.content_frame()
                if frame:
                    frame_btn = frame.locator("text='Pay Now', text='Place Order'")
                    if await frame_btn.count() > 0:
                        await frame_btn.first.click()
                        print("Clicked payment button inside iframe.")
                        return "Clicked payment button inside iframe."

            print("Could not find 'Pay Now' button (timeout or not in DOM).")
            return "Could not find Pay Now button."

        except Exception as e:
            print(f"Error clicking Pay Now: {e}")
            return f"Error: {str(e)}"
