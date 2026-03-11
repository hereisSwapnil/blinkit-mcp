from mcp.server.fastmcp import FastMCP, Image
from src.auth import BlinkitAuth
from src.order.blinkit_order import BlinkitOrder
import io
import asyncio
from contextlib import redirect_stdout
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize FastMCP
SERVE_SSE = os.environ.get("SERVE_HTTPS", "").lower() == "true"

print(SERVE_SSE)

if SERVE_SSE:
    mcp = FastMCP("blinkit-mcp", host="0.0.0.0", port=8000)
else:
    mcp = FastMCP("blinkit-mcp")

# Marker files for background Playwright install status
_INSTALL_MARKER = os.path.expanduser("~/.blinkit_mcp/.playwright_installing")
_INSTALL_DONE_MARKER = os.path.expanduser("~/.blinkit_mcp/.playwright_ready")


def _is_playwright_installing() -> bool:
    """Check if the background Playwright install is still running."""
    return os.path.exists(_INSTALL_MARKER)


async def _wait_for_playwright_install(timeout: float = 120.0) -> bool:
    """Wait for the background Playwright install to finish. Returns True if ready."""
    if not _is_playwright_installing():
        return True

    print("Playwright browser is being installed in the background. Waiting...")
    elapsed = 0.0
    while _is_playwright_installing() and elapsed < timeout:
        await asyncio.sleep(1.0)
        elapsed += 1.0

    if _is_playwright_installing():
        print(f"Playwright install still running after {timeout}s.")
        return False

    print("Playwright browser install finished.")
    return True


# Global Context to maintain session
class BlinkitContext:
    def __init__(self):
        # Explicitly use the shared session path
        import os

        session_path = os.path.expanduser("~/.blinkit_mcp/cookies/auth.json")
        headless = os.environ.get("HEADLESS", "true").lower() == "true"
        self.auth = BlinkitAuth(headless=headless, session_path=session_path)
        self.order = None

    async def ensure_started(self):
        # If Playwright browser is being installed in the background, wait for it
        if _is_playwright_installing():
            ready = await _wait_for_playwright_install(timeout=120.0)
            if not ready:
                raise RuntimeError(
                    "Playwright Firefox browser is still being downloaded. "
                    "Please wait a moment and try again."
                )

        # Check if browser/page is active. If page is closed, restart.
        restart = False
        if not self.auth.page:
            restart = True
        else:
            try:
                # Check if page is still connected
                if self.auth.page.is_closed():
                    restart = True
                else:
                    # Optional: Check browser context too
                    pass
            except Exception:
                restart = True

        if restart:
            print("Browser not active or closed. Launching...")
            try:
                await self.auth.start_browser()
            except Exception as e:
                error_msg = str(e)
                if "Executable doesn't exist" in error_msg:
                    # Playwright browser binary is missing — may still be installing
                    if _is_playwright_installing():
                        raise RuntimeError(
                            "Playwright Firefox is still being downloaded in the background. "
                            "Please wait a moment and try again."
                        )
                    else:
                        raise RuntimeError(
                            "Playwright Firefox browser is not installed. "
                            "Please run: playwright install firefox"
                        )
                raise
            self.order = BlinkitOrder(self.auth.page)
        elif self.order is None and self.auth.page:
            # Browser is active but order object missing (e.g. from partial failure or manual restart)
            self.order = BlinkitOrder(self.auth.page)


ctx = BlinkitContext()


@mcp.tool()
async def check_login() -> str:
    """Check if the current session is logged in. Returns 'Logged In' or 'Not Logged In'."""
    await ctx.ensure_started()
    if await ctx.auth.is_logged_in():
        # Refresh session file
        await ctx.auth.save_session()
        return "Logged In"
    return "Not Logged In"


@mcp.tool()
async def set_location(location_name: str) -> str:
    """Manually set the delivery location via search. Pass 'detect' to click 'Detect my location'. The flow should be: login -> set_location('detect') -> add items -> check_cart -> if address not same, use get_addresses and select_address. Do not use this tool to fix address after adding items."""
    await ctx.ensure_started()
    await ctx.order.set_location(location_name)
    return f"Location search initiated for {location_name}. Please check result."


@mcp.tool()
async def login(phone_number: str) -> str:
    """Log in to Blinkit. Returns status or prompts for OTP (which will be sent to your phone)."""
    await ctx.ensure_started()

    # Check session first
    if await ctx.auth.is_logged_in():
        return "Already logged in with valid session."

    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.auth.login(phone_number)
    return f.getvalue()


@mcp.tool()
async def enter_otp(otp: str) -> str:
    """Enter the OTP received on your phone to complete authentication."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.auth.enter_otp(otp)
        if await ctx.auth.is_logged_in():
            await ctx.auth.save_session()
            print("Session saved successfully.")
        else:
            print("Login verification might have failed or is still processing.")
    return f.getvalue()


@mcp.tool()
async def search(query: str) -> str:
    """Search for a product on Blinkit. Returns a list of items with their IDs."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.search_product(query)
        results = await ctx.order.get_search_results()
        if results:
            print(f"\nFound {len(results)} results:")
            for item in results:
                print(
                    f"[{item['index']}] ID: {item['id']} | {item['name']} - {item['price']}"
                )
        else:
            print("No results found.")
    return f.getvalue()


@mcp.tool()
async def add_to_cart(item_id: str, quantity: int = 1) -> str:
    """Add an item to the cart. Optional: specify quantity (default 1)."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.add_to_cart(item_id, quantity)
    return f.getvalue()


@mcp.tool()
async def remove_from_cart(item_id: str, quantity: int = 1) -> str:
    """Remove a specific quantity of an item from the cart."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.remove_from_cart(item_id, quantity)
    return f.getvalue()


@mcp.tool()
async def check_cart() -> str:
    """Check the current cart products, total value, and the delivery address. If the delivery address is not the intended one, use get_addresses and select_address to change it."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        content = await ctx.order.get_cart_items()

    return f.getvalue() + "\nCart Details:\n" + str(content)


@mcp.tool()
async def checkout() -> str:
    """Proceed to checkout (clicks Proceed / Pay button). DO NOT call this if you need to change the delivery address. To change address, use get_addresses and select_address BEFORE checkout! Do not use set_location to fix address here."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.place_order()
    return f.getvalue()


@mcp.tool()
async def get_addresses() -> str:
    """Get the list of saved addresses. Use this and select_address to change address on the cart page, if the address in check_cart is incorrect."""
    await ctx.ensure_started()
    addresses = await ctx.order.get_saved_addresses()
    if not addresses:
        return (
            "No addresses found or Address Modal is not open. Try to open kart first."
        )

    out = "Saved Addresses:\n"
    for addr in addresses:
        out += f"[{addr['index']}] {addr['label']} - {addr['details']}\n"
    return out


@mcp.tool()
async def select_address(index: int) -> str:
    """Select a delivery address by its index. Only use this BEFORE checkout."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.select_address(index)
    return f.getvalue()


@mcp.tool()
async def proceed_to_pay() -> str:
    """Proceed to payment (clicks Proceed button again). Use after selecting address."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.place_order()
    return f.getvalue()


@mcp.tool()
async def select_payment_method():
    """Select a payment method. Automatically chooses Cash on Delivery if available. If not, it opens UPI and generates a QR code to be scanned by the customer."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        res = await ctx.order.select_payment_method()
        if isinstance(res, dict):
            status = res.get("status", "")
            print(status)
            import base64
            import os
            import sys
            import subprocess

            b64_data = res.get("qr_base64")
            img_format = res.get("format", "png")

            # Save the image locally and open it for the user
            qr_path = os.path.abspath(f"payment_qr.{img_format}")
            try:
                with open(qr_path, "wb") as f_img:
                    f_img.write(base64.b64decode(b64_data))

                # Automatically open the image
                if sys.platform == "darwin":
                    subprocess.run(["open", qr_path])
                elif sys.platform.startswith("linux"):
                    subprocess.run(["xdg-open", qr_path])
                elif sys.platform == "win32":
                    os.startfile(qr_path)
            except Exception as e:
                print(f"Failed to save/open QR code image: {e}")

            img = Image(
                data=base64.b64decode(b64_data),
                format=img_format,
            )

            instruction = f"\n\n[INSTRUCTION TO AI: The QR Code has been saved to '{qr_path}' and automatically opened on the user's screen. Tell the user to check the newly opened image window to scan the QR code and complete their payment. DO NOT try to render the image in your response via markdown.]\n"
            return [f.getvalue() + instruction, img]
        elif res:
            print(res)
    return f.getvalue()


@mcp.tool()
async def pay_now() -> str:
    """Click the 'Pay Now' button to complete the transaction."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.click_pay_now()
    return f.getvalue()


@mcp.tool()
async def check_availability_across_locations(
    product_name: str, locations: list[str]
) -> str:
    """
    Check product availability across multiple locations/pincodes.
    Useful to verify if a product is available in different areas.

    Args:
        product_name: Name of the product to search for
        locations: List of location names or pincodes to check (e.g. ["Mumbai 400001", "Delhi 110001"])

    Returns:
        Availability status for each location including store status and products found.
    """
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        print(
            f"Checking availability of '{product_name}' across {len(locations)} locations..."
        )
        results = await ctx.order.check_product_availability(product_name, locations)

        print(f"\n{'='*60}")
        print(f"AVAILABILITY REPORT: {product_name}")
        print(f"{'='*60}\n")

        for result in results:
            print(f"Location: {result['location']}")
            print(f"  Store Status: {result['store_status']}")
            print(f"  Available: {'Yes' if result['available'] else 'No'}")

            if result.get("error"):
                print(f"  Error: {result['error']}")
            elif result["available"] and result["products_found"]:
                print(f"  Products Found: {len(result['products_found'])}")
                for product in result["products_found"][:3]:  # Show top 3
                    print(f"    - {product['name']} at {product['price']}")
            print()

        # Summary
        available_count = sum(1 for r in results if r["available"])
        print(f"Summary: Product available in {available_count}/{len(results)} locations")
        print(f"{'='*60}\n")

    return f.getvalue()
