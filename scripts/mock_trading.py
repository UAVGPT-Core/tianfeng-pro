#!/usr/bin/env python3
"""
LGOX联邦 模拟交易闭环引擎 v1.0
===============================
虚拟账户→信号→下单→持仓→盯市→盈亏→基因反馈
零外部依赖,纯stdlib+sqlite3

部署: 天枢(Mac Studio) /Users/a1/stockagent-backend/mock_trading.py
数据库: /Users/a1/stockagent-data/mock_trading.db
基因注入: 地枢LGE 100.116.0.29:8200
"""

import sqlite3, json, urllib.request, time, logging, os, sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger("mock_trading")
DB_PATH = "/Users/a1/stockagent-data/mock_trading.db"
LGE_URL = "http://100.116.0.29:8200/genes/write"

# ═══════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════
INITIAL_CAPITAL = 1_000_000.0       # 初始资金 100万
POSITION_SIZE_RATIO = 0.10          # 单笔仓位10%
TAKE_PROFIT_PCT = 0.20              # 止盈 +20%
STOP_LOSS_PCT = 0.08                # 止损 -8%
MIN_CONFIDENCE = 70                 # 最低置信度(百分制)
MAX_POSITIONS = 5                   # 最大同时持仓数
MIN_HOLD_DAYS = 2                   # 最少持有天数(防止过度交易)
COMMISSION_RATE = 0.0003            # 佣金费率 万三
STAMP_TAX_RATE = 0.001              # 印花税(卖出) 千一

# ═══════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════

@dataclass
class Account:
    """虚拟账户"""
    id: int = 1
    initial_capital: float = INITIAL_CAPITAL
    cash: float = INITIAL_CAPITAL
    equity: float = INITIAL_CAPITAL      # 总资产 = cash + market_value
    market_value: float = 0.0             # 持仓市值
    margin: float = 0.0                   # 已用保证金
    total_pnl: float = 0.0                # 累计盈亏
    total_pnl_pct: float = 0.0
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    created_at: str = ""
    updated_at: str = ""

@dataclass  
class Position:
    """虚拟持仓"""
    id: int = 0
    symbol: str = ""             # ts_code: 600519.SH
    name: str = ""               # 股票名称
    side: str = "long"           # long/short (当前仅做多)
    quantity: int = 0            # 持仓股数(手×100)
    available_qty: int = 0       # 可用股数
    entry_price: float = 0.0     # 开仓均价
    current_price: float = 0.0   # 最新价
    cost: float = 0.0            # 成本=quantity×entry_price
    market_value: float = 0.0    # 市值=quantity×current_price
    unrealized_pnl: float = 0.0  # 浮动盈亏
    unrealized_pnl_pct: float = 0.0
    signal_id: int = 0           # 触发信号ID
    entry_date: str = ""         # 开仓日期
    hold_days: int = 0
    status: str = "open"         # open / closed

@dataclass
class Trade:
    """交易记录"""
    id: int = 0
    symbol: str = ""
    name: str = ""
    side: str = "buy"            # buy / sell
    quantity: int = 0
    price: float = 0.0
    amount: float = 0.0          # 成交金额
    commission: float = 0.0      # 佣金
    stamp_tax: float = 0.0       # 印花税
    confidence: float = 0.0      # 信号置信度
    signal_id: int = 0
    reason: str = ""             # signal_open / take_profit / stop_loss / manual
    pnl_realized: float = 0.0    # 实现盈亏(卖出时)
    pnl_pct: float = 0.0
    result: str = ""             # win / loss / pending
    trade_date: str = ""
    pnl_recorded: int = 0        # 是否已写基因

@dataclass
class DailyPnL:
    """每日盈亏快照"""
    date: str = ""
    start_equity: float = 0.0
    end_equity: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    trade_count: int = 0
    open_positions: int = 0
    win_rate_daily: float = 0.0

# ═══════════════════════════════════════════════
# 数据库层
# ═══════════════════════════════════════════════

def get_db() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def init_db():
    """建表 (幂等)"""
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY DEFAULT 1,
        initial_capital REAL NOT NULL,
        cash REAL NOT NULL,
        equity REAL NOT NULL,
        market_value REAL DEFAULT 0,
        margin REAL DEFAULT 0,
        total_pnl REAL DEFAULT 0,
        total_pnl_pct REAL DEFAULT 0,
        total_trades INTEGER DEFAULT 0,
        win_trades INTEGER DEFAULT 0,
        loss_trades INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        name TEXT DEFAULT '',
        side TEXT DEFAULT 'long',
        quantity INTEGER NOT NULL,
        available_qty INTEGER NOT NULL,
        entry_price REAL NOT NULL,
        current_price REAL DEFAULT 0,
        cost REAL DEFAULT 0,
        market_value REAL DEFAULT 0,
        unrealized_pnl REAL DEFAULT 0,
        unrealized_pnl_pct REAL DEFAULT 0,
        signal_id INTEGER DEFAULT 0,
        entry_date TEXT DEFAULT (date('now','localtime')),
        hold_days INTEGER DEFAULT 0,
        status TEXT DEFAULT 'open'
    );
    CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);

    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        name TEXT DEFAULT '',
        side TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        amount REAL DEFAULT 0,
        commission REAL DEFAULT 0,
        stamp_tax REAL DEFAULT 0,
        confidence REAL DEFAULT 0,
        signal_id INTEGER DEFAULT 0,
        reason TEXT DEFAULT 'signal_open',
        pnl_realized REAL DEFAULT 0,
        pnl_pct REAL DEFAULT 0,
        result TEXT DEFAULT 'pending',
        trade_date TEXT DEFAULT (date('now','localtime')),
        pnl_recorded INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date);

    CREATE TABLE IF NOT EXISTS daily_pnl (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        start_equity REAL DEFAULT 0,
        end_equity REAL DEFAULT 0,
        pnl REAL DEFAULT 0,
        pnl_pct REAL DEFAULT 0,
        trade_count INTEGER DEFAULT 0,
        open_positions INTEGER DEFAULT 0,
        win_rate_daily REAL DEFAULT 0
    );

    -- 信号交易记录 (去重: 同一信号不重复开仓)
    CREATE TABLE IF NOT EXISTS signal_trades (
        signal_id INTEGER PRIMARY KEY,
        symbol TEXT,
        traded INTEGER DEFAULT 0,
        trade_date TEXT
    );
    """)

    # 初始化账户 (幂等)
    existing = conn.execute("SELECT id FROM accounts WHERE id=1").fetchone()
    if not existing:
        conn.execute("""
            INSERT INTO accounts (id, initial_capital, cash, equity, created_at, updated_at)
            VALUES (1, ?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))
        """, (INITIAL_CAPITAL, INITIAL_CAPITAL, INITIAL_CAPITAL))
    
    conn.commit()
    conn.close()
    logger.info("✅ mock_trading DB ready")

# ═══════════════════════════════════════════════
# 核心引擎
# ═══════════════════════════════════════════════

class MockTradingEngine:
    """模拟交易引擎"""

    def __init__(self):
        init_db()

    def get_account(self) -> dict:
        """获取账户状态"""
        conn = get_db()
        row = conn.execute("SELECT * FROM accounts WHERE id=1").fetchone()
        conn.close()
        if row:
            return dict(row)
        return {"error": "no account"}

    def get_positions(self, status: str = "open") -> list:
        """获取持仓列表"""
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM positions WHERE status=? ORDER BY entry_date DESC", (status,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_trades(self, limit: int = 50) -> list:
        """获取交易记录"""
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_daily_pnl(self, days: int = 30) -> list:
        """获取每日盈亏"""
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM daily_pnl ORDER BY date DESC LIMIT ?", (days,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_equity_curve(self) -> list:
        """获取权益曲线(近60日)"""
        conn = get_db()
        rows = conn.execute(
            "SELECT date, end_equity FROM daily_pnl ORDER BY date ASC LIMIT 60"
        ).fetchall()
        conn.close()
        return [{"date": r["date"], "equity": r["end_equity"]} for r in rows]

    def open_position(self, symbol: str, name: str, signal_id: int, 
                       confidence: float, direction: str = "buy") -> dict:
        """
        开仓: 信号置信度≥MIN_CONFIDENCE时触发
        以次日开盘价成交
        """
        conn = get_db()

        # 检查信号是否已交易
        existing = conn.execute(
            "SELECT traded FROM signal_trades WHERE signal_id=?", (signal_id,)
        ).fetchone()
        if existing and existing["traded"]:
            conn.close()
            return {"error": f"signal {signal_id} already traded", "status": "duplicate"}

        # 检查持仓数量限制
        open_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM positions WHERE status='open'"
        ).fetchone()
        if open_count["cnt"] >= MAX_POSITIONS:
            conn.close()
            return {"error": f"max positions ({MAX_POSITIONS}) reached", "status": "limit"}

        # 检查置信度
        if confidence < MIN_CONFIDENCE:
            conn.close()
            return {"error": f"confidence {confidence} < {MIN_CONFIDENCE}", "status": "low_conf"}

        # 获取账户
        acc = conn.execute("SELECT * FROM accounts WHERE id=1").fetchone()
        if not acc:
            conn.close()
            return {"error": "no account"}

        # 获取当前价格 (从新浪日K线)
        current_price = self._get_latest_price(symbol)
        if current_price <= 0:
            conn.close()
            return {"error": f"cannot get price for {symbol}", "status": "no_price"}

        # 计算仓位
        max_amount = acc["equity"] * POSITION_SIZE_RATIO
        quantity = int(max_amount / current_price / 100) * 100  # 整百股
        if quantity < 100:
            conn.close()
            return {"error": f"position too small: {quantity} shares", "status": "too_small"}

        amount = quantity * current_price
        commission = amount * COMMISSION_RATE
        total_cost = amount + commission

        if total_cost > acc["cash"]:
            # 降仓
            quantity = int((acc["cash"] * 0.95) / current_price / 100) * 100
            if quantity < 100:
                conn.close()
                return {"error": "insufficient cash", "status": "no_cash"}
            amount = quantity * current_price
            commission = amount * COMMISSION_RATE
            total_cost = amount + commission

        # 开仓交易记录
        today = datetime.now().strftime("%Y-%m-%d")
        conn.execute("""
            INSERT INTO trades (symbol, name, side, quantity, price, amount, commission,
                              confidence, signal_id, reason, trade_date, result)
            VALUES (?, ?, 'buy', ?, ?, ?, ?, ?, ?, 'signal_open', ?, 'pending')
        """, (symbol, name, quantity, current_price, amount, commission, confidence, signal_id, today))

        # 更新持仓
        conn.execute("""
            INSERT INTO positions (symbol, name, side, quantity, available_qty,
                                   entry_price, current_price, cost, market_value,
                                   signal_id, entry_date, status)
            VALUES (?, ?, 'long', ?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (symbol, name, quantity, quantity, current_price, current_price,
              total_cost, quantity * current_price, signal_id, today))

        # 更新账户
        new_cash = acc["cash"] - total_cost
        new_market_value = acc["market_value"] + amount
        new_equity = new_cash + new_market_value
        conn.execute("""
            UPDATE accounts SET cash=?, market_value=?, equity=?, 
            total_trades=total_trades+1, updated_at=datetime('now','localtime')
            WHERE id=1
        """, (new_cash, new_market_value, new_equity))

        # 记录信号已交易
        conn.execute(
            "INSERT OR REPLACE INTO signal_trades (signal_id, symbol, traded, trade_date) VALUES (?, ?, 1, ?)",
            (signal_id, symbol, today)
        )

        conn.commit()
        conn.close()

        return {
            "status": "opened",
            "symbol": symbol,
            "name": name,
            "quantity": quantity,
            "price": current_price,
            "amount": amount,
            "commission": commission,
            "signal_id": signal_id,
            "confidence": confidence,
            "cash_remaining": round(new_cash, 2),
            "equity": round(new_equity, 2)
        }

    def close_position(self, position_id: int, reason: str = "manual",
                        exit_price: float = None) -> dict:
        """平仓"""
        conn = get_db()

        pos = conn.execute(
            "SELECT * FROM positions WHERE id=? AND status='open'", (position_id,)
        ).fetchone()
        if not pos:
            conn.close()
            return {"error": "position not found or already closed"}

        # 获取当前价格
        if exit_price is None or exit_price <= 0:
            exit_price = self._get_latest_price(pos["symbol"])
        if exit_price <= 0:
            exit_price = pos["current_price"]  # fallback

        quantity = pos["quantity"]
        sell_amount = quantity * exit_price
        commission = sell_amount * COMMISSION_RATE
        stamp_tax = sell_amount * STAMP_TAX_RATE  # 卖出收印花税
        net_proceeds = sell_amount - commission - stamp_tax

        # 计算盈亏
        cost = pos["cost"]
        pnl_realized = net_proceeds - cost
        pnl_pct = (pnl_realized / cost * 100) if cost > 0 else 0
        result = "win" if pnl_realized > 0 else "loss"

        today = datetime.now().strftime("%Y-%m-%d")

        # 卖出交易记录
        conn.execute("""
            INSERT INTO trades (symbol, name, side, quantity, price, amount, commission,
                              stamp_tax, signal_id, reason, pnl_realized, pnl_pct, result, trade_date)
            VALUES (?, ?, 'sell', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pos["symbol"], pos["name"], quantity, exit_price, sell_amount,
              commission, stamp_tax, pos["signal_id"], reason, pnl_realized, pnl_pct, result, today))

        # 更新持仓为已平
        conn.execute("""
            UPDATE positions SET status='closed', current_price=?, market_value=?,
            unrealized_pnl=?, unrealized_pnl_pct=?, hold_days=
            CAST(julianday('now') - julianday(entry_date) AS INTEGER)
            WHERE id=?
        """, (exit_price, sell_amount, pnl_realized, pnl_pct, position_id))

        # 更新账户
        acc = conn.execute("SELECT * FROM accounts WHERE id=1").fetchone()
        new_cash = acc["cash"] + net_proceeds
        new_total_pnl = acc["total_pnl"] + pnl_realized
        new_win = acc["win_trades"] + (1 if result == "win" else 0)
        new_loss = acc["loss_trades"] + (1 if result != "win" else 0)
        # 更新市值
        remaining_mv = conn.execute(
            "SELECT COALESCE(SUM(market_value),0) as mv FROM positions WHERE status='open'"
        ).fetchone()["mv"]
        new_equity = new_cash + remaining_mv

        conn.execute("""
            UPDATE accounts SET cash=?, market_value=?, equity=?, 
            total_pnl=?, total_pnl_pct=?, total_trades=total_trades+1,
            win_trades=?, loss_trades=?,
            updated_at=datetime('now','localtime')
            WHERE id=1
        """, (new_cash, remaining_mv, new_equity, new_total_pnl,
              (new_total_pnl / INITIAL_CAPITAL * 100), new_win, new_loss))

        conn.commit()
        conn.close()

        # 基因反馈
        self._feed_gene(pos, pnl_realized, pnl_pct, result, reason)

        return {
            "status": "closed",
            "symbol": pos["symbol"],
            "pnl_realized": round(pnl_realized, 2),
            "pnl_pct": round(pnl_pct, 2),
            "result": result,
            "reason": reason
        }

    def mark_to_market(self) -> dict:
        """每日盯市: 更新所有持仓最新价 + 生成日盈亏快照"""
        conn = get_db()
        today = datetime.now().strftime("%Y-%m-%d")

        # 更新所有持仓最新价
        positions = conn.execute(
            "SELECT * FROM positions WHERE status='open'"
        ).fetchall()

        total_mv = 0
        total_upnl = 0
        for pos in positions:
            latest = self._get_latest_price(pos["symbol"])
            if latest > 0:
                mv = pos["quantity"] * latest
                upnl = mv - pos["cost"]
                upnl_pct = (upnl / pos["cost"] * 100) if pos["cost"] > 0 else 0
                conn.execute("""
                    UPDATE positions SET current_price=?, market_value=?,
                    unrealized_pnl=?, unrealized_pnl_pct=?,
                    hold_days=CAST(julianday('now') - julianday(entry_date) AS INTEGER)
                    WHERE id=?
                """, (latest, mv, upnl, upnl_pct, pos["id"]))
                total_mv += mv
                total_upnl += upnl

        # 更新账户
        acc = conn.execute("SELECT * FROM accounts WHERE id=1").fetchone()
        new_equity = acc["cash"] + total_mv
        new_total_pnl = new_equity - acc["initial_capital"]
        conn.execute("""
            UPDATE accounts SET market_value=?, equity=?, total_pnl=?, total_pnl_pct=?,
            updated_at=datetime('now','localtime') WHERE id=1
        """, (total_mv, new_equity, new_total_pnl,
              (new_total_pnl / acc["initial_capital"] * 100)))

        # 生成或更新今日快照
        existing = conn.execute("SELECT date FROM daily_pnl WHERE date=?", (today,)).fetchone()
        if existing:
            conn.execute("""
                UPDATE daily_pnl SET end_equity=?, pnl=?, pnl_pct=?,
                trade_count=(SELECT COUNT(*) FROM trades WHERE trade_date=?),
                open_positions=(SELECT COUNT(*) FROM positions WHERE status='open')
                WHERE date=?
            """, (new_equity, new_total_pnl,
                  (new_total_pnl / acc["initial_capital"] * 100),
                  today, today))
        else:
            conn.execute("""
                INSERT INTO daily_pnl (date, start_equity, end_equity, pnl, pnl_pct,
                    trade_count, open_positions)
                VALUES (?, ?, ?, ?, ?, 
                    (SELECT COUNT(*) FROM trades WHERE trade_date=?),
                    (SELECT COUNT(*) FROM positions WHERE status='open'))
            """, (today, acc["initial_capital"], new_equity, new_total_pnl,
                  (new_total_pnl / acc["initial_capital"] * 100), today))

        conn.commit()

        # 检查止盈止损
        self._check_stops(conn)

        conn.close()

        return {
            "date": today,
            "equity": round(new_equity, 2),
            "pnl": round(new_total_pnl, 2),
            "pnl_pct": round(new_total_pnl / INITIAL_CAPITAL * 100, 2),
            "market_value": round(total_mv, 2),
            "cash": round(acc["cash"], 2),
            "open_positions": len(positions)
        }

    def _check_stops(self, conn):
        """检查止盈止损"""
        positions = conn.execute(
            "SELECT * FROM positions WHERE status='open'"
        ).fetchall()
        for pos in positions:
            if pos["unrealized_pnl_pct"] >= TAKE_PROFIT_PCT * 100:
                self.close_position(pos["id"], reason="take_profit", exit_price=pos["current_price"])
            elif pos["unrealized_pnl_pct"] <= -STOP_LOSS_PCT * 100:
                self.close_position(pos["id"], reason="stop_loss", exit_price=pos["current_price"])

    def _get_latest_price(self, symbol: str) -> float:
        """从新浪日K线获取最新收盘价"""
        try:
            # symbol: 600519.SH → sh600519
            parts = symbol.split(".")
            code = parts[0]
            market = parts[1].lower() if len(parts) > 1 else "sh"
            sina_sym = f"{market}{code}"

            url = (f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                   f"CN_MarketData.getKLineData?symbol={sina_sym}&scale=240&ma=no&datalen=3")
            
            req = urllib.request.Request(url)
            req.add_header("Referer", "https://finance.sina.com.cn")
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    return float(data[-1]["close"])
        except Exception as e:
            logger.warning(f"get price failed for {symbol}: {e}")
        
        return 0.0

    def _feed_gene(self, pos: dict, pnl: float, pnl_pct: float, 
                     result: str, reason: str):
        """盈亏→LGE基因反馈"""
        try:
            if result == "win":
                gene_type = "GENE-TRADE-WIN"
                content = (
                    f"【交易盈利】【{pos['symbol']} {pos['name']}】"
                    f"入场{pos['entry_price']}→出场{pos['current_price']:.2f}，"
                    f"盈亏+{pnl:.2f}(+{pnl_pct:.1f}%)，"
                    f"持有{pos.get('hold_days','?')}天，"
                    f"平仓原因:{reason}。"
                    f"信号ID:{pos['signal_id']}。"
                    f"策略有效标记:该信号方向正确。"
                )
                tags = ["trade-win", "mock-trading", pos["symbol"], reason]
            else:
                gene_type = "GENE-TRADE-LOSS"
                content = (
                    f"【交易亏损】【{pos['symbol']} {pos['name']}】"
                    f"入场{pos['entry_price']}→出场{pos['current_price']:.2f}，"
                    f"盈亏{pnl:.2f}({pnl_pct:.1f}%)，"
                    f"持有{pos.get('hold_days','?')}天，"
                    f"平仓原因:{reason}。"
                    f"信号ID:{pos['signal_id']}。"
                    f"反模式:该信号在此条件下失效，应避免类似场景。"
                )
                tags = ["trade-loss", "mock-trading", pos["symbol"], reason, "anti-pattern"]

            gene_data = {
                "content": content,
                "memory_type": "semantic",
                "source": "mock-trading-feedback",
                "tags": tags,
                "node": "天枢"
            }

            req = urllib.request.Request(
                LGE_URL,
                data=json.dumps(gene_data, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
            logger.info(f"gene fed: {gene_type} {pos['symbol']}")
        except Exception as e:
            logger.warning(f"gene feed failed: {e}")

    def auto_trade_from_signals(self, signals: list) -> dict:
        """
        从信号列表自动交易 (cron调用入口)
        signals: [{"symbol": "600519.SH", "name": "贵州茅台", 
                    "signal_id": 123, "confidence": 85, "direction": "buy"}, ...]
        """
        results = {"opened": [], "skipped": [], "closed": []}

        # 先更新盯市
        self.mark_to_market()

        # 处理信号 - 按置信度排序
        sorted_signals = sorted(signals, key=lambda s: s.get("confidence", 0), reverse=True)

        for sig in sorted_signals:
            symbol = sig.get("symbol", "")
            name = sig.get("name", "")
            signal_id = sig.get("signal_id", 0)
            confidence = sig.get("confidence", 0)
            direction = sig.get("direction", "buy")

            if direction == "sell":
                # 卖出信号: 平掉该股持仓
                conn = get_db()
                pos = conn.execute(
                    "SELECT id FROM positions WHERE symbol=? AND status='open'", (symbol,)
                ).fetchone()
                conn.close()
                if pos:
                    res = self.close_position(pos["id"], reason="signal_sell")
                    results["closed"].append(res)
                else:
                    results["skipped"].append({"symbol": symbol, "reason": "no position"})
            else:
                # 买入信号
                res = self.open_position(symbol, name, signal_id, confidence)
                if "error" in res:
                    results["skipped"].append({"symbol": symbol, "reason": res.get("error", "")})
                else:
                    results["opened"].append(res)

        return results

    def reset(self) -> dict:
        """重置账户 (危险操作)"""
        conn = get_db()
        conn.executescript("""
            DELETE FROM positions;
            DELETE FROM trades;
            DELETE FROM daily_pnl;
            DELETE FROM signal_trades;
            UPDATE accounts SET cash=?, equity=?, market_value=0, total_pnl=0,
                total_pnl_pct=0, total_trades=0, win_trades=0, loss_trades=0,
                updated_at=datetime('now','localtime') WHERE id=1
        """)
        conn.execute("INSERT INTO accounts (id,initial_capital,cash,equity) VALUES (1,?,?,?) "
                      "ON CONFLICT(id) DO UPDATE SET cash=?,equity=?,total_pnl=0",
                      (INITIAL_CAPITAL, INITIAL_CAPITAL, INITIAL_CAPITAL,
                       INITIAL_CAPITAL, INITIAL_CAPITAL))
        conn.commit()
        conn.close()
        return {"status": "reset", "capital": INITIAL_CAPITAL}


# ═══════════════════════════════════════════════
# 现金流 (汇总报表)
# ═══════════════════════════════════════════════

def get_summary() -> dict:
    """获取完整状态快照"""
    engine = MockTradingEngine()
    account = engine.get_account()
    positions = engine.get_positions("open")
    recent_trades = engine.get_trades(10)
    daily = engine.get_daily_pnl(30)
    equity = engine.get_equity_curve()

    # 计算指标
    closed_trades = [t for t in engine.get_trades(200) if t.get("result") in ("win", "loss")]
    wins = [t for t in closed_trades if t.get("result") == "win"]
    losses = [t for t in closed_trades if t.get("result") == "loss"]

    win_rate = len(wins) / len(closed_trades) * 100 if closed_trades else 0
    total_wins = sum(t.get("pnl_realized", 0) for t in wins)
    total_losses = abs(sum(t.get("pnl_realized", 0) for t in losses))
    profit_factor = total_wins / total_losses if total_losses > 0 else 999

    return {
        "account": account,
        "positions": positions,
        "recent_trades": recent_trades,
        "daily_pnl": daily,
        "equity_curve": equity,
        "metrics": {
            "win_rate": round(win_rate, 1),
            "total_trades": len(closed_trades),
            "wins": len(wins),
            "losses": len(losses),
            "profit_factor": round(profit_factor, 2),
            "total_pnl": round(sum(t.get("pnl_realized", 0) for t in closed_trades), 2),
            "avg_win": round(total_wins / len(wins), 2) if wins else 0,
            "avg_loss": round(total_losses / len(losses), 2) if losses else 0,
        }
    }


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="LGOX Mock Trading Engine")
    ap.add_argument("action", nargs="?", default="summary",
                    choices=["init", "summary", "mtm", "reset", "account", "positions", "trades"])
    ap.add_argument("--signal-file", help="JSON signals file for auto_trade")
    args = ap.parse_args()

    engine = MockTradingEngine()

    if args.action == "init":
        init_db()
        print("✅ Mock trading DB initialized")
    elif args.action == "summary":
        s = get_summary()
        print(json.dumps(s, indent=2, ensure_ascii=False, default=str))
    elif args.action == "mtm":
        r = engine.mark_to_market()
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.action == "reset":
        r = engine.reset()
        print(json.dumps(r, indent=2))
    elif args.action == "account":
        a = engine.get_account()
        print(json.dumps(a, indent=2, ensure_ascii=False))
    elif args.action == "positions":
        p = engine.get_positions("open")
        print(json.dumps(p, indent=2, ensure_ascii=False))
    elif args.action == "trades":
        t = engine.get_trades(20)
        print(json.dumps(t, indent=2, ensure_ascii=False))
    elif args.action == "auto":
        if not args.signal_file:
            print("Need --signal-file")
            sys.exit(1)
        with open(args.signal_file) as f:
            signals = json.load(f)
        r = engine.auto_trade_from_signals(signals)
        print(json.dumps(r, indent=2, ensure_ascii=False))
