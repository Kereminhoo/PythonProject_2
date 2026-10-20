from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    stop_price: float
    target_price: Optional[float]
    entry_time: object
    unrealized_pnl: float = 0.0
    entry_signal_score: int = 0
    entry_metrics: dict = field(default_factory=dict)

    initial_stop_price: float = 0.0
    highest_price: float = 0.0
    current_r: float = 0.0
    stop_r: float = -1.0
    trailing_active: bool = False
    stop_update_count: int = 0


@dataclass
class ClosedTrade:
    symbol: str
    entry_time: object
    exit_time: object
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    entry_commission: float = 0.0
    exit_commission: float = 0.0
    slippage_cost: float = 0.0
    entry_signal_score: int = 0
    entry_metrics: dict = field(default_factory=dict)


@dataclass
class Portfolio:
    initial_capital: float
    cash: float
    commission_pct: float = 0.0
    
    # Alpaca Standart Reg-T / Margin Buying Power Çarpanı (2.5x)
    # 3 pozisyonun da kırpılmadan tam R riskiyle açılmasını sağlar!
    buying_power_multiplier: float = 2.5

    positions: Dict[str, Position] = field(default_factory=dict)
    closed_trades: List[ClosedTrade] = field(default_factory=list)
    equity_curve: List[dict] = field(default_factory=list)

    def calculate_equity(self, prices: dict = None) -> float:
        if prices is None:
            prices = {}
        equity = float(self.cash)
        for symbol, position in self.positions.items():
            current_price = prices.get(symbol)
            if current_price is None:
                current_price = position.entry_price
            equity += position.quantity * float(current_price)
        return float(equity)

    def get_buying_power(self, prices: dict = None) -> float:
        equity = self.calculate_equity(prices)
        if equity <= 0:
            return 0.0
        invested = sum(
            pos.quantity * pos.entry_price for pos in self.positions.values()
        )
        return max((equity * self.buying_power_multiplier) - invested, 0.0)

    def update_unrealized_pnl(self, prices: dict):
        for symbol, position in self.positions.items():
            current_price = prices.get(symbol)
            if current_price is None:
                continue
            position.unrealized_pnl = (
                float(current_price) - position.entry_price
            ) * position.quantity

    def open_position(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        stop_price: float,
        target_price: Optional[float],
        entry_time,
        entry_signal_score: int = 0,
        entry_metrics: dict = None,
    ):
        if entry_metrics is None:
            entry_metrics = {}
        if symbol in self.positions:
            raise ValueError(f"{symbol}: zaten açık pozisyon var.")

        quantity = float(quantity)
        entry_price = float(entry_price)
        stop_price = float(stop_price)
        if target_price is not None:
            target_price = float(target_price)

        if quantity <= 0 or entry_price <= 0:
            raise ValueError(f"{symbol}: geçersiz quantity veya entry_price.")
        if stop_price <= 0 or stop_price >= entry_price:
            raise ValueError(f"{symbol}: geçersiz stop price.")
        if target_price is not None and target_price <= entry_price:
            raise ValueError(f"{symbol}: geçersiz target price.")

        position_value = quantity * entry_price
        entry_commission = position_value * self.commission_pct
        total_cost = position_value + entry_commission

        available_bp = self.get_buying_power()
        if total_cost > (available_bp + 1e-6):
            raise ValueError(
                f"{symbol}: yeterli alım gücü yok. Gerekli=${total_cost:.2f}, BP=${available_bp:.2f}"
            )

        self.cash -= total_cost

        self.positions[symbol] = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            entry_time=entry_time,
            unrealized_pnl=0.0,
            entry_signal_score=entry_signal_score,
            entry_metrics=entry_metrics,
            initial_stop_price=stop_price,
            highest_price=entry_price,
            current_r=0.0,
            stop_r=-1.0,
            trailing_active=False,
            stop_update_count=0,
        )

    def update_position_state(
        self,
        symbol: str,
        current_price: float,
    ) -> Optional[Position]:
        if symbol not in self.positions:
            return None
        position = self.positions[symbol]
        current_price = float(current_price)
        if current_price <= 0:
            return position
        if current_price > position.highest_price:
            position.highest_price = current_price

        initial_risk = position.entry_price - position.initial_stop_price
        if initial_risk > 0:
            position.current_r = (current_price - position.entry_price) / initial_risk
        else:
            position.current_r = 0.0
        return position

    def update_stop_price(self, symbol: str, new_stop_price: float) -> bool:
        if symbol not in self.positions:
            return False
        position = self.positions[symbol]
        new_stop_price = float(new_stop_price)
        if new_stop_price <= 0 or new_stop_price <= position.stop_price:
            return False
        if new_stop_price >= position.highest_price:
            return False

        position.stop_price = new_stop_price
        position.stop_update_count += 1
        position.trailing_active = True

        initial_risk = position.entry_price - position.initial_stop_price
        if initial_risk > 0:
            position.stop_r = (new_stop_price - position.entry_price) / initial_risk
        return True

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_time,
        exit_reason: str,
    ):
        if symbol not in self.positions:
            raise ValueError(f"{symbol}: açık pozisyon bulunamadı.")
        position = self.positions[symbol]
        exit_price = float(exit_price)
        if exit_price <= 0:
            raise ValueError(f"{symbol}: exit_price > 0 olmalıdır.")

        gross_pnl = (exit_price - position.entry_price) * position.quantity
        entry_value = position.entry_price * position.quantity
        exit_value = exit_price * position.quantity

        entry_commission = entry_value * self.commission_pct
        exit_commission = exit_value * self.commission_pct
        net_pnl = gross_pnl - entry_commission - exit_commission
        pnl_pct = (net_pnl / entry_value) if entry_value > 0 else 0.0

        holding_seconds = None
        try:
            holding_seconds = (exit_time - position.entry_time).total_seconds()
        except (AttributeError, TypeError):
            pass
        holding_minutes = holding_seconds / 60.0 if holding_seconds is not None else None

        self.cash += (exit_value - exit_commission)

        trade_metrics = dict(position.entry_metrics)
        trade_metrics.update({
            "holding_minutes": holding_minutes,
            "gross_pnl": gross_pnl,
            "entry_value": entry_value,
            "exit_value": exit_value,
            "return_on_entry_pct": pnl_pct * 100,
            "initial_stop_price": position.initial_stop_price,
            "final_stop_price": position.stop_price,
            "highest_price": position.highest_price,
            "final_r": position.current_r,
            "stop_r": position.stop_r,
            "trailing_active": position.trailing_active,
            "stop_update_count": position.stop_update_count,
        })

        trade = ClosedTrade(
            symbol=symbol,
            entry_time=position.entry_time,
            exit_time=exit_time,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            pnl=net_pnl,
            pnl_pct=pnl_pct,
            exit_reason=exit_reason,
            entry_commission=entry_commission,
            exit_commission=exit_commission,
            slippage_cost=0.0,
            entry_signal_score=position.entry_signal_score,
            entry_metrics=trade_metrics,
        )

        self.closed_trades.append(trade)
        del self.positions[symbol]
        return trade

    def record_equity(
        self,
        timestamp,
        prices: dict,
        daily_start_equity: float = None,
        daily_return_pct: float = None,
        daily_loss_limit_hit: bool = False,
        daily_tp1_hit: bool = False,
        daily_tp2_hit: bool = False,
    ):
        self.update_unrealized_pnl(prices)
        equity = self.calculate_equity(prices)
        self.equity_curve.append({
            "timestamp": timestamp,
            "equity": float(equity),
            "cash": float(self.cash),
            "open_positions": len(self.positions),
            "daily_start_equity": float(daily_start_equity) if daily_start_equity is not None else None,
            "daily_return_pct": float(daily_return_pct) if daily_return_pct is not None else None,
            "daily_loss_limit_hit": bool(daily_loss_limit_hit),
            "daily_tp1_hit": bool(daily_tp1_hit),
            "daily_tp2_hit": bool(daily_tp2_hit),
        })