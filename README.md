<p align="center">
  <img src="assets/logo.png" alt="Blinkit MCP Logo" width="120" height="120" style="border-radius:30px;">
</p>

<h1 align="center">Unofficial Blinkit MCP</h1>

<p align="center">
  A Model Context Protocol (MCP) server that lets Claude Desktop browse, search, and order from Blinkit in real time.
</p>

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License">
  </a>
  <img src="https://img.shields.io/badge/python-3.12+-green.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/MCP-Claude%20Desktop-purple.svg" alt="Claude MCP">
</p>

---

## ✨ What is Blinkit MCP?

**Blinkit MCP** is a plug-and-play MCP server that allows Claude Desktop to automate your grocery shopping on Blinkit.

Your AI can:
- 🔍 Search for products (groceries, electronics, etc.)
- 🛒 Add items to your cart
- 📍 Manage delivery locations
- 💳 Automate checkout and UPI payments
- 🔐 Login securely with phone and OTP

No manual clicking required. Just ask Claude to buy milk.

---

## 🎬 Quick Demo

https://github.com/user-attachments/assets/531f09ad-648a-4ee2-9271-5993ce637093

> 💡 *Ask Claude: "Buy milk from Blinkit"*

---

## 🚀 Quick Start (30 seconds)

1. **Install `uv`** (if you don't have it):

   **macOS / Linux**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   **Windows**
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **(Optional) Pre-install Browsers**  
   If you want to speed up the first run:
   ```bash
   uvx playwright install chromium
   # OR if you have Node.js:
   # npx playwright install chromium
   ```

3. **Download the MCP bundle**  
   👉 [blinkit-mcp.mcpb](https://github.com/hereisSwapnil/blinkit-mcp/releases/download/v1.0.2/blinkit-mcp.mcpb)

4. **Double-click** the `.mcpb` file — Claude Desktop installs it automatically.

5. **Open Claude Desktop** and start shopping.

---

## 🔥 Key Features

| Feature | Description |
|---------|-------------|
| 🔒 **Secure Auth** | Login via Phone Number & OTP (Session persisted locally) |
| 🔎 **Smart Search** | Find products by name and get pricing/details |
| 🛒 **Cart Management** | Add items, check cart status, and verify availability |
| 📍 **Location** | Detect or manually set delivery location |
| 🌍 **Multi-Location Check** | **New!** Check product availability across different pincodes/locations |
| 💳 **Payment Automation** | Select saved UPI IDs or enter new ones automatically |
| 🚀 **Checkout Flow** | Handles address selection and ordering flow seamlessly |

---

## 📦 One-Click Installation (Recommended)

Download and install directly in Claude Desktop:

<p align="center">
  <a href="https://github.com/hereisSwapnil/blinkit-mcp/releases/download/v1.0.2/blinkit-mcp.mcpb">
    <img src="https://img.shields.io/badge/Download-blinkit--mcp.mcpb-orange?style=for-the-badge" alt="Download">
  </a>
</p>

**Supports:** macOS • Windows • Linux

---

## 🛠️ Manual Installation

If you prefer to run from source:

1. **Clone and Run**:
   ```bash
   git clone https://github.com/hereisSwapnil/blinkit-mcp.git
   cd blinkit-mcp
   
   # Install uv (if needed)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install Python dependencies
   uv sync
   
   # Install Playwright browsers
   uv run playwright install chromium
   
   # Run the server
   uv run main.py
   ```

2. **Configure Claude Desktop**:
   
   Add this to your `claude_desktop_config.json`:

   ```json
   {
     "mcpServers": {
       "blinkit-mcp": {
         "command": "/usr/local/bin/uv",
         "args": ["run", "main.py"],
         "cwd": "/absolute/path/to/blinkit-mcp",
         "env": {
             "HEADLESS": "false" 
         }
       }
     }
   }
   ```
   *(Set `HEADLESS` to `false` to see the browser action, or `true` for background mode)*

## 🧰 Available MCP Tools

| Tool | Description |
|------|-------------|
| `check_login` | Check if currently logged in |
| `login` | Login with phone number |
| `enter_otp` | Verify login with OTP |
| `set_location` | Manually search and set delivery location |
| `search` | Search for products |
| `add_to_cart` | Add product to cart by index |
| `remove_from_cart` | Remove item from cart |
| `check_cart` | View cart contents |
| `checkout` | Proceed to checkout |
| `get_addresses` | Get list of saved addresses |
| `select_address` | Select a delivery address |
| `proceed_to_pay` | Proceed to payment page |
| `get_upi_ids` | List available UPI payment options |
| `select_upi_id` | Select a specific UPI ID for payment |
| `pay_now` | Click the final Pay Now button |
| `check_availability_across_locations` | Check product availability across multiple pincodes/locations |

---

## 💬 Example Queries

- *"Buy milk from Blinkit to my home and use my UPI for payment"*
- *"Order 2 packets of Maggi and pay via UPI"*
- *"Get me some chips, deliver to office, and checkout"*
- *"Check if Amul milk is available in Mumbai 400001, Delhi 110001, and Bangalore 560001"*
- *"Is bread available across pincodes in Maharashtra?"*

---

## 📁 Project Structure

```
blinkit-mcp/
├── main.py                # MCP server entry point
├── src/
│   ├── auth/              # Authentication module
│   │   └── service.py     # Auth service implementation
│   ├── order/             # Order management module
│   │   ├── blinkit_order.py   # Main order controller
│   │   └── services/          # Domain services
│   │       ├── base.py        # Base service class
│   │       ├── search.py      # Search logic
│   │       ├── location.py    # Location logic
│   │       ├── cart.py        # Cart logic
│   │       └── checkout.py    # Checkout & Payment logic
│   └── server.py          # MCP Tool definitions
├── test/
│   └── cli.py             # CLI for testing independent of Claude
└── README.md
```

---

## 📄 License

Licensed under the [MIT License](LICENSE).

---

  <b>Blinkit MCP turns Claude into your personal grocery assistant.</b>
</p>

---

## ⚠️ Disclaimer

This project is an **experimental** proof of concept and is **not affiliated, associated, authorized, endorsed by, or in any way officially connected with Blinkit (Grofers India Private Limited)**, or any of its subsidiaries or its affiliates. The official Blinkit website can be found at [blinkit.com](https://blinkit.com).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=hereisSwapnil/blinkit-mcp&type=date&legend=top-left)](https://www.star-history.com/#hereisSwapnil/blinkit-mcp&type=date&legend=top-left)

---
