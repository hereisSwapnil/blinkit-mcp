from mcp.server.fastmcp import FastMCP
from src.auth.blinkit_auth import BlinkitAuth
from src.order.blinkit_order import BlinkitOrder
import io
from contextlib import redirect_stdout

import os

# Initialize FastMCP
SERVE_SSE = os.environ.get("SERVE_HTTPS", "").lower() == "true"

if SERVE_SSE:
    mcp = FastMCP("blinkit-mcp", host="0.0.0.0", port=8000)
else:
    mcp = FastMCP("blinkit-mcp")


# Global Context to maintain session
class BlinkitContext:
    def __init__(self):
        # Explicitly use the shared session path
        import os

        session_path = os.path.expanduser("~/.blinkit_mcp/cookies/auth.json")
        self.auth = BlinkitAuth(headless=False, session_path=session_path)
        self.order = None

    async def ensure_started(self):
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
            await self.auth.start_browser()
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
    """Manually set the delivery location via search. Use this if 'Detect my location' sets the wrong place."""
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
    """Search for a product on Blinkit. Returns a list of items with indexes."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.search_product(query)
        results = await ctx.order.get_search_results()
        if results:
            print(f"\nFound {len(results)} results:")
            for item in results:
                print(f"[{item['index']}] {item['name']} - {item['price']}")
        else:
            print("No results found.")
    return f.getvalue()


@mcp.tool()
async def add_to_cart(item_index: int) -> str:
    """Add an item to the cart using its result index. Run search() first."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.add_to_cart(item_index)
    return f.getvalue()


@mcp.tool()
async def check_cart() -> str:
    """Check the current cart products and total value."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        content = await ctx.order.get_cart_items()

    return f.getvalue() + "\nCart Details:\n" + str(content)


@mcp.tool()
async def checkout() -> str:
    """Proceed to checkout (clicks Proceed/Checkout button). Triggers address selection if needed."""
    await ctx.ensure_started()
    f = io.StringIO()
    with redirect_stdout(f):
        await ctx.order.place_order()
    return f.getvalue()


@mcp.tool()
async def get_addresses() -> str:
    """Get the list of saved addresses if the address selection modal is open."""
    await ctx.ensure_started()
    addresses = await ctx.order.get_saved_addresses()
    if not addresses:
        return "No addresses found or Address Modal is not open. Try 'checkout' first."

    out = "Saved Addresses:\n"
    for addr in addresses:
        out += f"[{addr['index']}] {addr['label']} - {addr['details']}\n"
    return out


@mcp.tool()
async def select_address(index: int) -> str:
    """Select a delivery address by its index."""
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
