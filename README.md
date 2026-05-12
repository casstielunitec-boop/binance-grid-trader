# 🦞 Binance Spot Grid Trader

**Automated grid trading bot for Binance Spot. Buy low, sell high, 24/7.**

> 💰 **Price: $5 USD** — One-time payment, lifetime access, free updates.

## 💳 How to Buy (30 Seconds)

Send **$5 USDT** to any of these addresses, then open an Issue saying "paid" with your TXID:

| Network | Address | Fee |
|---------|---------|-----|
| **BSC (BEP20)** | `0x717c80a5de505ede7d6ca2c3d8ce699e3431e7d0` | ~$0.01 |
| **TRON (TRC20)** | `TN8S5pYpF9qHS6PN2a9FtTubk4ah7MkCCV` | ~$1 |
| **Polygon** | `0x717c80a5de505ede7d6ca2c3d8ce699e3431e7d0` | ~$0.001 |

> 💡 **BSC recommended** — lowest fees. The code is already here and works. If it makes you money, pay it forward. 🦞

---

## What You Get

✅ **Working Python script** — Ready to run on Windows, Mac, or Linux  
✅ **Grid trading strategy** — Automatically buys at grid lows, sells at grid highs  
✅ **Dry-run mode** — Test with zero risk before going live  
✅ **Stop-loss protection** — Automatic emergency exit  
✅ **Real-time logging** — See every trade as it happens  
✅ **State persistence** — Survives restarts, remembers your grid  
✅ **Clean, documented code** — Easy to customize  
✅ **Setup guide** — Step-by-step instructions below  

---

## How Grid Trading Works

```
Price ↑
$84,000 ┤  SELL ← your sell orders fill here
$83,400 ┤
$82,800 ┤
$82,200 ┤  (current price)
$81,600 ┤
$81,000 ┤
$80,400 ┤
$79,800 ┤  BUY  ← your buy orders fill here
$78,000 ┤
        └──────────────────────────→ Time

Each time price crosses a grid line:
  BUY → fills at lower level
  SELL → automatically placed at next level up
  PROFIT = spread between levels
```

The bot places buy orders at each level below the current price. When a buy fills, it immediately places a sell order one level higher. When that sells, it places a new buy at the original level. **You profit from the spread, over and over.**

---

## Quick Start (5 Minutes)

### 1. Install Python Dependencies
```bash
pip install requests python-dotenv
```

### 2. Get Binance API Keys
1. Go to [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2. Click "Create API Key"
3. **Enable Spot Trading** (only "Enable Spot & Margin Trading" needed)
4. **Do NOT enable withdrawals** (safety!)
5. Copy your API Key and Secret

### 3. Configure
```bash
# Create .env file
cp .env.example .env

# Edit .env with your keys:
# BINANCE_API_KEY=your_key_here
# BINANCE_API_SECRET=your_secret_here
```

### 4. Test with Dry Run
```bash
python grid_trader.py --dry-run
```
This simulates trading without spending real money. Watch the logs to understand the strategy.

### 5. Go Live!
```bash
python grid_trader.py --live
```

---

## Configuration

Edit `GridConfig` in `grid_trader.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `SYMBOL` | BTCUSDT | Trading pair |
| `GRID_LOWER` | 78000 | Bottom of grid (USDT) |
| `GRID_UPPER` | 84000 | Top of grid (USDT) |
| `GRID_LEVELS` | 10 | Number of grid lines |
| `ORDER_SIZE` | 0.0005 | BTC per grid level |
| `STOP_LOSS_PCT` | 5.0 | Emergency stop % below grid |
| `REFRESH_SEC` | 15 | Check interval (seconds) |

**Profit per round-trip:**  
`ORDER_SIZE × (GRID_UPPER - GRID_LOWER) / GRID_LEVELS`  
*Example:* 0.0005 BTC × $600 spread = **$0.30 per fill**

---

## Commands

```bash
# Dry run (test mode)
python grid_trader.py --dry-run

# Live trading
python grid_trader.py --live

# Single cycle
python grid_trader.py --once

# View grid status
python grid_trader.py --status

# Cancel all orders
python grid_trader.py --cancel
```

---

## Safety Features

🛡️ **Stop-loss** — Auto-cancels all orders if price drops below 5% of grid  
🛡️ **No withdrawals** — API key only needs trading permission  
🛡️ **Dry-run mode** — Test everything before risking real money  
🛡️ **State file** — All orders tracked in `grid_state.json`  

---

## FAQ

**Q: How much capital do I need?**  
A: Minimum ~$50 USDT for BTCUSDT with default settings. More capital = more grid levels = more profit.

**Q: What if price goes outside the grid?**  
A: If price goes above the grid, all your BTC gets sold (profit!). If below, the stop-loss triggers.

**Q: Can I use other coins?**  
A: Yes! Change `SYMBOL` to any Binance USDT pair (e.g., ETHUSDT, BNBUSDT).

**Q: Does this work 24/7?**  
A: Yes! Run it on a VPS or keep your computer on.

**Q: Refund policy?**  
A: 30-day money-back guarantee. Not satisfied? Full refund, no questions.

---

## Requirements

- Python 3.8+
- Binance account with API keys
- Internet connection

---

**Made with 🦞 | Price: $5 | Instant Download**
