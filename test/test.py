import sys
import os
import asyncio

# Add project root to Python path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth.blinkit_auth import BlinkitAuth
from src.order.blinkit_order import BlinkitOrder


async def get_input(prompt: str) -> str:
    return await asyncio.to_thread(input, prompt)


async def main():
    # Initialize Auth
    # Headless=False to see the browser and debug
    auth = BlinkitAuth(headless=False)

    try:
        print("Starting browser...")
        await auth.start_browser()

        # Check if already logged in
        await auth.page.wait_for_timeout(3000)

        if not await auth.is_logged_in():
            print("Not logged in.")
            phone = await get_input("Enter your phone number: ")
            await auth.login(phone)

            otp = await get_input("Enter the OTP you received: ")
            await auth.enter_otp(otp)

            print("Waiting for login to complete...")
            await auth.page.wait_for_timeout(5000)

            if await auth.is_logged_in():
                print("Login successful!")
                await auth.save_session()
            else:
                print("Login failed or could not verify.")
                return

        print("Already logged in! Session valid.")

        # Initialize Order
        order = BlinkitOrder(auth.page)

        print("\n" + "=" * 50)
        print("      Welcome to Blinkit CLI Automation")
        print("=" * 50)
        print("Commands:")
        print("  search <query>   : Search for products (default: milk)")
        print("  add <index>      : Add item at index to cart")
        print("  cart             : View/Check cart status")
        print("  checkout         : Proceed to checkout & address selection")
        print("  address          : Manually trigger address selection")
        print("  login            : Re-initiate login flow")
        print("  quit / exit      : Close and exit")
        print("=" * 50 + "\n")

        while True:
            try:
                # Use async input to avoid blocking loop
                user_input = (await get_input("blinkit> ")).strip()
                if not user_input:
                    continue

                parts = user_input.split()
                cmd = parts[0].lower()
                args = parts[1:]

                if cmd in ["quit", "exit"]:
                    print("Exiting...")
                    break

                elif cmd == "help":
                    print(
                        "Commands: search <query>, add <index>, cart, checkout, address, login, quit"
                    )

                elif cmd == "login":
                    if not await auth.is_logged_in():
                        phone = await get_input("Enter phone number: ")
                        await auth.login(phone)
                        otp = await get_input("Enter OTP: ")
                        await auth.enter_otp(otp)
                        if await auth.is_logged_in():
                            await auth.save_session()
                    else:
                        print("Already logged in.")

                elif cmd == "search":
                    term = " ".join(args) if args else "milk"
                    await order.search_product(term)
                    results = await order.get_search_results()
                    if results:
                        print("\nSearch Results:")
                        for item in results:
                            print(f"[{item['index']}] {item['name']} - {item['price']}")
                    else:
                        print("No results found.")

                elif cmd == "add":
                    if args and args[0].isdigit():
                        await order.add_to_cart(int(args[0]))
                    else:
                        print("Usage: add <item_index>")

                elif cmd == "cart":
                    await order.get_cart_items()

                elif cmd == "address":
                    addresses = await order.get_saved_addresses()
                    if addresses:
                        print("\nSelect Delivery Address:")
                        for addr in addresses:
                            print(
                                f"[{addr['index']}] {addr['label']} - {addr['details'][:50]}..."
                            )

                        sel = await get_input("Select index (Enter to cancel): ")
                        if sel.strip().isdigit():
                            await order.select_address(int(sel))
                    else:
                        print("Address selection not available (modal not open?).")

                elif cmd == "checkout":
                    await order.place_order()
                    print("Checking for address selection after checkout...")
                    await auth.page.wait_for_timeout(2000)
                    # Auto-check address
                    addresses = await order.get_saved_addresses()
                    if addresses:
                        print("\nSelect Delivery Address:")
                        for addr in addresses:
                            print(
                                f"[{addr['index']}] {addr['label']} - {addr['details'][:50]}..."
                            )

                        sel = await get_input("Select index (Enter to keep current): ")
                        if sel.strip().isdigit():
                            await order.select_address(int(sel))
                            await order.place_order()

                else:
                    print(f"Unknown command: {cmd}")

            except KeyboardInterrupt:
                print("\nType 'quit' to exit.")
                break
            except Exception as e:
                print(f"Error executing command: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Check if auth is defined before closing
        if "auth" in locals():
            await auth.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
