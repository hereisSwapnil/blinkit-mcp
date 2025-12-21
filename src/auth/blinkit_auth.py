import os
from playwright.async_api import async_playwright


class BlinkitAuth:
    def __init__(self, headless: bool = False, session_path: str = None):
        self.headless = headless
        if session_path:
            self.session_path = session_path
        else:
            # Use a safe directory in home folder to avoid permission/read-only issues
            self.session_path = os.path.expanduser("~/.blinkit_mcp/cookies/auth.json")

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start_browser(self):
        """Starts the Playwright browser (Firefox)."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.firefox.launch(headless=self.headless)

        if os.path.exists(self.session_path):
            print(f"Loading session from {self.session_path}")
            self.context = await self.browser.new_context(
                storage_state=self.session_path,
                permissions=["geolocation"],
                geolocation={
                    "latitude": 28.6279,
                    "longitude": 77.3649,
                },  # Default to Noida Sector 62
            )
        else:
            print("No existing session found. Starting fresh.")
            self.context = await self.browser.new_context(
                permissions=["geolocation"],
                geolocation={"latitude": 28.6279, "longitude": 77.3649},
            )

        self.page = await self.context.new_page()
        await self.page.goto("https://blinkit.com/")
        print("Opened Blinkit.com")

        # Handle "Detect my location" popup if it appears
        try:
            print("Checking for location popup...")
            location_btn = self.page.locator("button", has_text="Detect my location")
            try:
                # Wait briefly to see if it appears
                await location_btn.wait_for(state="visible", timeout=3000)
                print("Location popup detected. Clicking 'Detect my location'...")
                await location_btn.click()
                # Wait for it to disappear potentially
                await location_btn.wait_for(state="hidden", timeout=5000)
            except Exception:
                # Timed out waiting for it, probably didn't appear or already handled
                pass
        except Exception as e:
            print(f"Note: Error checking location popup: {e}")

        # Check for global unavailability message on Homepage
        try:
            if await self.page.is_visible("text=Currently unavailable"):
                print(
                    "WARNING: Store is marked as 'Currently unavailable' on the homepage."
                )
        except Exception:
            pass

    async def login(self, phone_number: str):
        """Initiates the login process with a phone number."""
        print(f"Attempting to log in with {phone_number}...")

        # 1. Click Login Button
        try:
            # Try multiple strategies to find the Login button
            if await self.page.is_visible("text='Login'"):
                await self.page.click("text='Login'")
                print("Clicked 'Login' text.")
            elif await self.page.is_visible("div[class*='ProfileButton__Container']"):
                await self.page.locator(
                    "div[class*='ProfileButton__Container']"
                ).click()
                print("Clicked ProfileButton container.")
            else:
                print(
                    "Could not find explicit Login button. Checking if already on login screen..."
                )
        except Exception as e:
            print(f"Error clicking login button: {e}")

        # 2. Wait for Login Modal / Phone Input
        try:
            print("Waiting for phone number input...")
            # Increased timeout and generic selector
            phone_input = await self.page.wait_for_selector(
                "input[type='tel'], input[name='mobile'], input[type='text']",
                state="visible",
                timeout=5000,
            )

            if phone_input:
                await phone_input.click()
                await phone_input.fill(phone_number)
                print(f"Filled phone number: {phone_number}")

                # 3. Submit Phone Number
                await self.page.wait_for_timeout(500)  # slight delay for UI update

                # Check for "Get OTP" or "Next"
                if await self.page.is_visible("text='Next'"):
                    await self.page.click("text='Next'")
                elif await self.page.is_visible("text='Continue'"):
                    await self.page.click("text='Continue'")
                else:
                    # Fallback: press Enter on the input
                    await self.page.keyboard.press("Enter")
                    print("Pressed Enter to submit.")

            else:
                print("Phone input found but None returned?")

        except Exception as e:
            print(f"Error entering phone number: {e}")

    async def enter_otp(self, otp: str):
        """Enters the OTP."""
        try:
            print("Waiting for OTP input...")
            # Wait for any input to be visible (4 digit boxes or single input)
            await self.page.wait_for_selector("input", timeout=10000)

            # Check for OTP inputs
            inputs = self.page.locator("input")
            count = await inputs.count()

            if count == 4:
                print("Detected 4-digit OTP inputs.")
                for i, digit in enumerate(otp):
                    if i < 4:
                        await inputs.nth(i).fill(digit)
                        await self.page.wait_for_timeout(100)  # small delay
            else:
                # Single input?
                print(f"Detected {count} inputs. Trying to fill first/relevant one.")
                # Look for input with 'otp' in name or id or class
                otp_input = self.page.locator(
                    "input[data-test-id='otp-input'], input[name*='otp'], input[id*='otp']"
                ).first
                if await otp_input.is_visible():
                    await otp_input.fill(otp)
                else:
                    # Fallback: fill generic input
                    await self.page.fill("input", otp)

            print("Entered OTP. Waiting for auto-submit or button...")
            await self.page.keyboard.press("Enter")

        except Exception as e:
            print(f"Error entering OTP: {e}")

    async def is_logged_in(self) -> bool:
        """Checks if the user is logged in."""
        if not self.page or self.page.is_closed():
            return False

        try:
            if await self.page.is_visible(
                "text=My Account"
            ) or await self.page.is_visible(".user-profile"):
                return True

            if not await self.page.is_visible("text=Login"):
                return True

            return False
        except:
            return False

    async def save_session(self):
        """Saves functionality cookies to file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.session_path), exist_ok=True)
        await self.context.storage_state(path=self.session_path)
        print(f"Session saved to {self.session_path}")

    async def close(self):
        """Closes the browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
