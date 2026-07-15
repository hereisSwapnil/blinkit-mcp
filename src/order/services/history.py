import re
from datetime import datetime

from .base import BaseService

LIST_URL = "https://blinkit.com/account/orders"

_STATUS_RE = re.compile(r"Arrived|Delivered|Cancelled", re.I)
_TOTAL_RE = re.compile(r"₹[\d,]+")
_DATE_RE = re.compile(r"\d{1,2} [A-Za-z]{3},? \d{1,2}:\d{2}\s*[ap]m", re.I)

# container > wrapper > card (card classes are hashed; the BffOrderHistory
# prefix is stable, so anchor on it and filter cards by status text).
_CARD_SELECTOR = 'div[class*="BffOrderHistory"] > div > div'


class HistoryService(BaseService):
    # ---- pure parsers (no page interaction) ----

    @staticmethod
    def _parse_summary_text(text: str) -> dict:
        t = " ".join(text.split())  # collapse newlines/spaces -> uniform
        total_m = _TOTAL_RE.search(t)
        date_m = _DATE_RE.search(t)
        total = total_m.group(0) if total_m else ""
        date = date_m.group(0) if date_m else ""
        status = (t[: total_m.start()] if total_m else t).strip()
        return {"status": status, "total": total, "date": date}

    @staticmethod
    def _split_qty(qty_line: str):
        # "53 g x 1" -> ("53 g", 1); "2 x 750 ml x 1" -> ("2 x 750 ml", 1)
        parts = qty_line.rsplit(" x ", 1)
        if len(parts) == 2 and parts[1].strip().isdigit():
            return parts[0].strip(), int(parts[1].strip())
        return qty_line.strip(), 1

    @classmethod
    def _parse_detail_text(cls, text: str) -> dict:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        start = None
        for i, ln in enumerate(lines):
            if re.search(r"items? in this order", ln, re.I):
                start = i + 1
                break
        # Marker absent: return empty items rather than starting at line 0 and
        # folding page-header lines into the first item's name.
        if start is None:
            return {"items": [], "bill_total": ""}

        items = []
        buf = []
        for ln in lines[start:]:
            if re.match(r"bill details", ln, re.I):
                break
            if ln.startswith("₹") or ln.startswith("-₹"):
                if len(buf) >= 2:
                    variant, qty = cls._split_qty(buf[-1])
                    items.append({
                        "name": " ".join(buf[:-1]),
                        "variant": variant,
                        "quantity": qty,
                        "price": ln,
                    })
                buf = []
            else:
                buf.append(ln)

        bill_total = ""
        for i, ln in enumerate(lines):
            if re.fullmatch(r"bill total", ln, re.I):
                for nxt in lines[i + 1:]:
                    if nxt.startswith("₹"):
                        bill_total = nxt
                        break
                break

        return {"items": items, "bill_total": bill_total}

    # ---- pure formatting ----

    @staticmethod
    def _plural(n: int, singular: str) -> str:
        return f"{n} {singular}" + ("" if n == 1 else "s")

    @classmethod
    def _format_history(cls, orders: list, fetched: str) -> str:
        # Return the order history as-is (per order: date, total, status, items)
        # and let the consumer reason over it — deriving "what do I buy often"
        # from a short window is the LLM's job, not this tool's.
        lines = [
            f"Order history — last {cls._plural(len(orders), 'order')} (fetched {fetched})",
            "",
        ]
        for idx, o in enumerate(orders, 1):
            lines.append(
                f"[{idx}] {o['date']} · {o['total']} · {o['status']} · "
                f"{cls._plural(len(o['items']), 'item')}"
            )
            for it in o["items"]:
                variant = f" ({it['variant']})" if it["variant"] else ""
                lines.append(f"    - {it['name']}{variant} ×{it['quantity']} — {it['price']}")
            if o.get("error"):
                lines.append(f"    (could not load items: {o['error']})")

        return "\n".join(lines)

    # ---- orchestration (Playwright DOM) ----

    async def get_order_history(self, count: int = 10) -> str:
        page = self.page
        await page.goto(LIST_URL, wait_until="domcontentloaded")

        # Wait for a real order card, not just the structural selector: the page
        # first renders skeleton placeholders that match _CARD_SELECTOR but carry
        # no status text, so waiting on the bare selector would resolve on a
        # skeleton and then find zero status-bearing cards.
        cards = page.locator(_CARD_SELECTOR).filter(has_text=_STATUS_RE)
        try:
            await cards.first.wait_for(timeout=15000)
        except Exception:
            return (
                "No past orders found. If you are not logged in, "
                "run check_login / login first."
            )

        n = min(await cards.count(), count)
        if n == 0:
            return "No past orders found."

        orders = []
        for i in range(n):
            summary = {}
            try:
                # re-resolve after each back-navigation (DOM is re-rendered)
                cards = page.locator(_CARD_SELECTOR).filter(has_text=_STATUS_RE)
                card = cards.nth(i)
                summary = self._parse_summary_text(await card.inner_text())

                nav = card.locator('div[role="button"]').filter(has_text=_STATUS_RE).last
                await nav.scroll_into_view_if_needed()
                await nav.click()
                await page.wait_for_url("**/account/orders/*/*", timeout=15000)
                await page.wait_for_selector("text=/items? in this order/i", timeout=15000)
                detail = self._parse_detail_text(await page.inner_text("body"))
                error = None
            except Exception as e:
                detail = {"items": [], "bill_total": summary.get("total", "")}
                error = str(e)[:120]

            orders.append({
                "status": summary.get("status", ""),
                "total": summary.get("total", ""),
                "date": summary.get("date", ""),
                "items": detail["items"],
                "bill_total": detail["bill_total"],
                "error": error,
            })

            if i < n - 1:
                await page.goto(LIST_URL, wait_until="domcontentloaded")
                # wait for a status-bearing card, not the skeleton (see above)
                await page.locator(_CARD_SELECTOR).filter(
                    has_text=_STATUS_RE
                ).first.wait_for(timeout=15000)

        return self._format_history(orders, datetime.now().strftime("%d %b %Y"))
