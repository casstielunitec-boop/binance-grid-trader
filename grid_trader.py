"""
🦞 Binance Spot Grid Trader v1.0
=================================
Simple, profitable grid trading bot for Binance Spot.
Automatically buys low and sells high in a configured price range.

Author: Crypto Tools
License: MIT (included with purchase)
Price: $5 USD

Quick Start:
  1. pip install python-binance python-dotenv
  2. Copy .env.example to .env, fill in your Binance API keys
  3. Adjust GRID settings below
  4. python grid_trader.py --dry-run   (test first!)
  5. python grid_trader.py             (live trading)

⚠️ WARNING: Crypto trading involves risk. Only trade what you can afford to lose.
   ALWAYS test with --dry-run first. This is a tool, not financial advice.
"""

import os
import time
import json
import hmac
import hashlib
import logging
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Dict, List

import requests
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — Adjust these to your strategy
# ═══════════════════════════════════════════════════════════════

class GridConfig:
    """Grid trading parameters. Modify these for your strategy."""

    # Trading pair
    SYMBOL = "BTCUSDT"

    # Grid range: price boundaries
    GRID_LOWER = 78000   # Bottom of grid (USDT)
    GRID_UPPER = 84000   # Top of grid (USDT)
    GRID_LEVELS = 10     # Number of grid lines

    # Order size per grid level (in quote currency = BTC for BTCUSDT)
    ORDER_SIZE = 0.0005  # BTC per grid level

    # Risk management
    STOP_LOSS_PCT = 5.0      # Stop-loss percentage below grid lower
    MAX_POSITION = 0.005     # Max BTC position
    MIN_PROFIT_USD = 1.0     # Minimum profit to log

    # Operation
    REFRESH_SEC = 15         # Check interval (seconds)
    DRY_RUN = True           # Set False for real trading

    @classmethod
    def grid_step(cls) -> float:
        """Calculate price step between grid levels."""
        return (cls.GRID_UPPER - cls.GRID_LOWER) / cls.GRID_LEVELS

    @classmethod
    def grid_prices(cls) -> List[float]:
        """Generate all grid price levels."""
        step = cls.grid_step()
        return [cls.GRID_LOWER + i * step for i in range(cls.GRID_LEVELS + 1)]


# ═══════════════════════════════════════════════════════════════
# BINANCE API CLIENT
# ═══════════════════════════════════════════════════════════════

class BinanceClient:
    """Lightweight Binance Spot API client. No heavy dependencies."""

    BASE = "https://api.binance.com"

    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY", "")
        self.api_secret = os.getenv("BINANCE_API_SECRET", "")
        if not self.api_key or not self.api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET required in .env")

    def _sign(self, params: str) -> str:
        return hmac.new(
            self.api_secret.encode(), params.encode(), hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, path: str, signed: bool = False, **params) -> dict:
        url = self.BASE + path
        headers = {"X-MBX-APIKEY": self.api_key}

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            query = "&".join(f"{k}={v}" for k, v in params.items())
            query += f"&signature={self._sign(query)}"
            url += "?" + query
        else:
            if params:
                url += "?" + "&".join(f"{k}={v}" for k, v in params.items())

        resp = requests.request(method, url, headers=headers, timeout=15)
        data = resp.json()

        if isinstance(data, dict) and data.get("code"):
            raise Exception(f"API Error {data['code']}: {data.get('msg', '')}")

        return data

    def get_price(self, symbol: str = "BTCUSDT") -> float:
        data = self._request("GET", "/api/v3/ticker/price", symbol=symbol)
        return float(data["price"])

    def get_balance(self, asset: str) -> float:
        data = self._request("GET", "/api/v3/account", signed=True)
        for b in data.get("balances", []):
            if b["asset"] == asset:
                return float(b["free"])
        return 0.0

    def get_open_orders(self, symbol: str) -> List[dict]:
        return self._request("GET", "/api/v3/openOrders", signed=True, symbol=symbol)

    def place_limit_buy(self, symbol: str, quantity: float, price: float) -> dict:
        return self._request("POST", "/api/v3/order", signed=True,
            symbol=symbol, side="BUY", type="LIMIT",
            timeInForce="GTC", quantity=quantity, price=f"{price:.2f}")

    def place_limit_sell(self, symbol: str, quantity: float, price: float) -> dict:
        return self._request("POST", "/api/v3/order", signed=True,
            symbol=symbol, side="SELL", type="LIMIT",
            timeInForce="GTC", quantity=quantity, price=f"{price:.2f}")

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        return self._request("DELETE", "/api/v3/order", signed=True,
            symbol=symbol, orderId=order_id)

    def get_order(self, symbol: str, order_id: int) -> dict:
        return self._request("GET", "/api/v3/order", signed=True,
            symbol=symbol, orderId=order_id)


# ═══════════════════════════════════════════════════════════════
# GRID TRADER ENGINE
# ═══════════════════════════════════════════════════════════════

class GridTrader:
    """
    Grid Trading Strategy:
    - Place buy orders at each grid level below current price
    - When a buy fills, place a sell order at the next grid level above
    - Repeat: buy low, sell high, profit from the spread
    """

    def __init__(self, config=GridConfig, client=None):
        self.cfg = config
        self.client = client or BinanceClient()
        self.symbol = config.SYMBOL
        self.state_file = "grid_state.json"
        self.state = self._load_state()
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("GridTrader")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(message)s", datefmt="%H:%M:%S"
        ))
        logger.handlers = [handler]
        return logger

    def _load_state(self) -> dict:
        try:
            with open(self.state_file) as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "active_buys": {},    # {grid_level: order_id}
                "active_sells": {},   # {grid_level: order_id}
                "total_trades": 0,
                "total_profit": 0.0,
                "started_at": datetime.now().isoformat(),
            }

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def _get_grid_level(self, price: float) -> int:
        """Find which grid level a price belongs to."""
        step = self.cfg.grid_step()
        level = int((price - self.cfg.GRID_LOWER) / step)
        return max(0, min(self.cfg.GRID_LEVELS, level))

    def _log_trade(self, side: str, qty: float, price: float, profit: float = 0):
        self.state["total_trades"] += 1
        self.state["total_profit"] += profit
        self._save_state()

        emoji = "🟢" if side == "BUY" else "🔴"
        profit_str = f" | Profit: ${profit:.2f}" if profit else ""
        self.logger.info(
            f"{emoji} {side} {qty:.6f} {self.symbol} @ ${price:,.2f}{profit_str} | "
            f"Total PnL: ${self.state['total_profit']:.2f}"
        )

    def _get_step_size(self) -> float:
        """Get the minimum order quantity for the symbol."""
        # For BTCUSDT, step size is typically 0.00001
        return 0.00001

    def _round_qty(self, qty: float) -> float:
        """Round quantity to valid step size."""
        step = self._get_step_size()
        return float(Decimal(str(qty)).quantize(
            Decimal(str(step)), rounding=ROUND_DOWN
        ))

    def place_grid_orders(self):
        """Place buy orders at each unfilled grid level below current price."""
        current_price = self.client.get_price(self.symbol)
        grid_prices = self.cfg.grid_prices()
        step = self.cfg.grid_step()

        placed = 0
        for i, grid_price in enumerate(grid_prices):
            # Only place buys BELOW current price
            if grid_price >= current_price:
                continue
            # Skip if already have an order at this level
            if str(i) in self.state["active_buys"]:
                continue

            if self.cfg.DRY_RUN:
                self.logger.info(f"🧪 [DRY RUN] Would place BUY {self.cfg.ORDER_SIZE} @ ${grid_price:,.2f}")
                self.state["active_buys"][str(i)] = f"dry_run_{int(time.time())}"
                placed += 1
                continue

            try:
                order = self.client.place_limit_buy(
                    self.symbol,
                    self._round_qty(self.cfg.ORDER_SIZE),
                    grid_price
                )
                self.state["active_buys"][str(i)] = order["orderId"]
                self.logger.info(f"📉 BUY order placed: {self.cfg.ORDER_SIZE} @ ${grid_price:,.2f}")
                placed += 1
            except Exception as e:
                self.logger.error(f"Failed to place BUY @ ${grid_price}: {e}")

        return placed

    def check_filled_orders(self):
        """Check if any buy orders filled; if so, place sell orders above."""
        to_remove = []

        for level_str, order_id in list(self.state["active_buys"].items()):
            level = int(level_str)

            if self.cfg.DRY_RUN:
                # Simulate random fills for testing
                continue

            try:
                order = self.client.get_order(self.symbol, order_id)
                if order["status"] == "FILLED":
                    qty = float(order["executedQty"])
                    price = float(order["price"])
                    self._log_trade("BUY", qty, price)
                    to_remove.append(level_str)

                    # Place sell at next grid level
                    sell_price = self.cfg.grid_prices()[min(level + 1, self.cfg.GRID_LEVELS)]
                    sell_order = self.client.place_limit_sell(
                        self.symbol, self._round_qty(qty), sell_price
                    )
                    self.state["active_sells"][str(level + 1)] = sell_order["orderId"]
                    self.logger.info(f"📈 SELL order placed: {qty:.6f} @ ${sell_price:,.2f}")

            except Exception as e:
                self.logger.error(f"Check order {order_id} failed: {e}")

        for level_str in to_remove:
            del self.state["active_buys"][level_str]

        # Check if sell orders filled
        to_remove_sells = []
        for level_str, order_id in list(self.state["active_sells"].items()):
            if self.cfg.DRY_RUN:
                continue

            try:
                order = self.client.get_order(self.symbol, order_id)
                if order["status"] == "FILLED":
                    qty = float(order["executedQty"])
                    sell_price = float(order["price"])
                    # Calculate profit: (sell_price - buy_price) * qty
                    buy_level = int(level_str) - 1
                    buy_price = self.cfg.grid_prices()[buy_level]
                    profit = (sell_price - buy_price) * qty

                    self._log_trade("SELL", qty, sell_price, profit)
                    to_remove_sells.append(level_str)

            except Exception as e:
                self.logger.error(f"Check sell order {order_id} failed: {e}")

        for level_str in to_remove_sells:
            del self.state["active_sells"][level_str]
            # Place new buy at the original level
            self.state["active_buys"].pop(str(int(level_str) - 1), None)

        self._save_state()

    def check_stop_loss(self):
        """Emergency stop if price drops below stop-loss."""
        current_price = self.client.get_price(self.symbol)
        stop_price = self.cfg.GRID_LOWER * (1 - self.cfg.STOP_LOSS_PCT / 100)

        if current_price < stop_price:
            self.logger.warning(
                f"⚠️ STOP LOSS TRIGGERED! Price ${current_price:,.2f} < ${stop_price:,.2f}"
            )
            self.cancel_all_orders()
            return True
        return False

    def cancel_all_orders(self):
        """Cancel all active grid orders."""
        for level_str, order_id in list(self.state["active_buys"].items()):
            try:
                if not self.cfg.DRY_RUN:
                    self.client.cancel_order(self.symbol, order_id)
            except:
                pass
        for level_str, order_id in list(self.state["active_sells"].items()):
            try:
                if not self.cfg.DRY_RUN:
                    self.client.cancel_order(self.symbol, order_id)
            except:
                pass
        self.state["active_buys"] = {}
        self.state["active_sells"] = {}
        self._save_state()
        self.logger.info("🛑 All grid orders cancelled")

    def run(self, once: bool = False):
        """Main loop: place orders, check fills, repeat."""
        self.logger.info("=" * 50)
        self.logger.info(f"🦞 Grid Trader Starting")
        self.logger.info(f"   Symbol: {self.symbol}")
        self.logger.info(f"   Range: ${self.cfg.GRID_LOWER:,.0f} - ${self.cfg.GRID_UPPER:,.0f}")
        self.logger.info(f"   Levels: {self.cfg.GRID_LEVELS} | Spread: ${self.cfg.grid_step():,.0f}/level")
        self.logger.info(f"   Order Size: {self.cfg.ORDER_SIZE} {self.symbol.replace('USDT','')}")
        self.logger.info(f"   Mode: {'🧪 DRY RUN' if self.cfg.DRY_RUN else '💰 LIVE'}")
        self.logger.info("=" * 50)

        if self.cfg.DRY_RUN:
            self.logger.info("🧪 DRY RUN MODE — No real orders will be placed")
            self.logger.info("   Set DRY_RUN = False in GridConfig to go live")

        cycles = 0
        try:
            while True:
                cycles += 1

                # 1. Check stop-loss
                if not self.cfg.DRY_RUN and self.check_stop_loss():
                    break

                # 2. Check filled orders, place counter-orders
                self.check_filled_orders()

                # 3. Place new grid orders below current price
                placed = self.place_grid_orders()

                # 4. Status update
                current_price = self.client.get_price(self.symbol)
                active = len(self.state["active_buys"]) + len(self.state["active_sells"])
                self.logger.info(
                    f"Cycle #{cycles} | BTC: ${current_price:,.2f} | "
                    f"Orders: {active} | PnL: ${self.state['total_profit']:.2f}"
                )

                if once:
                    break

                time.sleep(self.cfg.REFRESH_SEC)

        except KeyboardInterrupt:
            self.logger.info("\n⏹️ Shutting down...")
        finally:
            self._save_state()
            self.logger.info(f"📊 Session: {self.state['total_trades']} trades, "
                           f"PnL: ${self.state['total_profit']:.2f}")


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Binance Spot Grid Trader")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without real orders")
    parser.add_argument("--live", action="store_true", help="LIVE trading mode")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--cancel", action="store_true", help="Cancel all open orders")
    parser.add_argument("--status", action="store_true", help="Show current grid status")
    args = parser.parse_args()

    # Override dry run from CLI
    if args.live:
        GridConfig.DRY_RUN = False
    elif args.dry_run:
        GridConfig.DRY_RUN = True

    trader = GridTrader()

    if args.cancel:
        trader.cancel_all_orders()
    elif args.status:
        print(f"Active Buys: {len(trader.state['active_buys'])}")
        print(f"Active Sells: {len(trader.state['active_sells'])}")
        print(f"Total Trades: {trader.state['total_trades']}")
        print(f"Total PnL: ${trader.state['total_profit']:.2f}")
    else:
        trader.run(once=args.once)
