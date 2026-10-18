from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============================================================
# POSITION
# ============================================================

@dataclass
class Position:

    symbol: str
    quantity: float

    entry_price: float

    # Current active stop.
    stop_price: float

    # Fixed target is kept for compatibility.
    # V2 normally does not use it as the primary exit.
    target_price: Optional[float]

    entry_time: object

    unrealized_pnl: float = 0.0

    entry_signal_score: int = 0
    entry_metrics: dict = field(default_factory=dict)

    # ========================================================
    # V2 TRADE MANAGEMENT STATE
    # ========================================================

    # Original stop never changes.
    initial_stop_price: float = 0.0

    # Highest market price observed while position is open.
    highest_price: float = 0.0

    # Current trade profit expressed in R.
    current_r: float = 0.0

    # Current stop expressed in R relative to entry.
    stop_r: float = -1.0

    # True when trailing logic has started managing the trade.
    trailing_active: bool = False

    # Number of stop updates.
    stop_update_count: int = 0


# ============================================================
# CLOSED TRADE
# ============================================================

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


# ============================================================
# PORTFOLIO
# ============================================================

@dataclass
class Portfolio:

    initial_capital: float
    cash: float

    commission_pct: float = 0.0

    positions: Dict[str, Position] = field(
        default_factory=dict
    )

    closed_trades: List[ClosedTrade] = field(
        default_factory=list
    )

    equity_curve: List[dict] = field(
        default_factory=list
    )

    # ========================================================
    # CURRENT EQUITY
    # ========================================================

    def calculate_equity(
        self,
        prices: dict,
    ) -> float:

        equity = float(
            self.cash
        )

        for symbol, position in (
            self.positions.items()
        ):

            current_price = (
                prices.get(symbol)
            )

            if current_price is None:

                current_price = (
                    position.entry_price
                )

            current_price = float(
                current_price
            )

            market_value = (
                position.quantity
                * current_price
            )

            equity += market_value

        return float(equity)

    # ========================================================
    # UNREALIZED P/L
    # ========================================================

    def update_unrealized_pnl(
        self,
        prices: dict,
    ):

        for symbol, position in (
            self.positions.items()
        ):

            current_price = (
                prices.get(symbol)
            )

            if current_price is None:
                continue

            current_price = float(
                current_price
            )

            position.unrealized_pnl = (
                current_price
                - position.entry_price
            ) * position.quantity

    # ========================================================
    # OPEN POSITION
    # ========================================================

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

        # ----------------------------------------------------
        # DUPLICATE
        # ----------------------------------------------------

        if symbol in self.positions:

            raise ValueError(
                f"{symbol}: zaten açık pozisyon var."
            )

        quantity = float(
            quantity
        )

        entry_price = float(
            entry_price
        )

        stop_price = float(
            stop_price
        )

        if target_price is not None:

            target_price = float(
                target_price
            )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if quantity <= 0:

            raise ValueError(
                f"{symbol}: quantity > 0 olmalıdır."
            )

        if entry_price <= 0:

            raise ValueError(
                f"{symbol}: entry_price > 0 olmalıdır."
            )

        if (
            stop_price <= 0
            or stop_price >= entry_price
        ):

            raise ValueError(
                f"{symbol}: geçersiz stop price."
            )

        # V2:
        # Sabit target kullanılmayabilir.
        if (
            target_price is not None
            and target_price <= entry_price
        ):

            raise ValueError(
                f"{symbol}: geçersiz target price."
            )

        # ----------------------------------------------------
        # POSITION VALUE
        # ----------------------------------------------------

        position_value = (
            quantity
            * entry_price
        )

        # ----------------------------------------------------
        # COMMISSION
        # ----------------------------------------------------

        entry_commission = (
            position_value
            * self.commission_pct
        )

        total_cost = (
            position_value
            + entry_commission
        )

        cash_tolerance = 1e-9

        if total_cost > (
            self.cash
            + cash_tolerance
        ):

            raise ValueError(
                f"{symbol}: yeterli nakit yok. "
                f"Gerekli=${total_cost:.2f}, "
                f"Cash=${self.cash:.2f}"
            )

        # ----------------------------------------------------
        # CASH
        # ----------------------------------------------------

        self.cash -= total_cost

        if (
            self.cash < 0
            and abs(self.cash) <= cash_tolerance
        ):

            self.cash = 0.0

        # ----------------------------------------------------
        # INITIAL RISK
        # ----------------------------------------------------

        initial_stop_distance = (
            entry_price
            - stop_price
        )

        initial_stop_r = -1.0

        if initial_stop_distance > 0:

            initial_stop_r = -1.0

        # ----------------------------------------------------
        # CREATE POSITION
        # ----------------------------------------------------

        self.positions[symbol] = Position(

            symbol=symbol,

            quantity=quantity,

            entry_price=entry_price,

            stop_price=stop_price,

            target_price=target_price,

            entry_time=entry_time,

            unrealized_pnl=0.0,

            entry_signal_score=(
                entry_signal_score
            ),

            entry_metrics=entry_metrics,

            initial_stop_price=(
                stop_price
            ),

            highest_price=(
                entry_price
            ),

            current_r=0.0,

            stop_r=initial_stop_r,

            trailing_active=False,

            stop_update_count=0,
        )

    # ========================================================
    # UPDATE POSITION STATE
    # ========================================================

    def update_position_state(
        self,
        symbol: str,
        current_price: float,
    ) -> Optional[Position]:
        """
        Pozisyonun trailing yönetimi için gerekli
        state bilgisini günceller.

        Henüz stop kararını vermez.
        Sadece:

            highest_price
            current_r

        değerlerini günceller.
        """

        if symbol not in self.positions:

            return None

        position = (
            self.positions[symbol]
        )

        current_price = float(
            current_price
        )

        if current_price <= 0:

            return position

        # ----------------------------------------------------
        # HIGHEST PRICE
        # ----------------------------------------------------

        if current_price > (
            position.highest_price
        ):

            position.highest_price = (
                current_price
            )

        # ----------------------------------------------------
        # CURRENT R
        # ----------------------------------------------------

        initial_risk = (
            position.entry_price
            - position.initial_stop_price
        )

        if initial_risk > 0:

            position.current_r = (
                current_price
                - position.entry_price
            ) / initial_risk

        else:

            position.current_r = 0.0

        return position

    # ========================================================
    # UPDATE STOP
    # ========================================================

    def update_stop_price(
        self,
        symbol: str,
        new_stop_price: float,
    ) -> bool:
        """
        Aktif stop'u ileri taşır.

        Long position için stop geriye çekilmez.

        Returns:
            True  -> stop güncellendi
            False -> update yapılmadı
        """

        if symbol not in self.positions:

            return False

        position = (
            self.positions[symbol]
        )

        new_stop_price = float(
            new_stop_price
        )

        if new_stop_price <= 0:

            return False

        # Stop entry'den yukarı çıkabilir.
        # Ancak entry'nin üzerinde olsa bile
        # fiyat mantığı bozulmamalı.
        if new_stop_price <= 0:
            return False

        if new_stop_price <= position.stop_price:
            return False

        reference_price = position.highest_price

        if new_stop_price >= reference_price:
            return False

        # ----------------------------------------------------
        # APPLY
        # ----------------------------------------------------

        position.stop_price = (
            new_stop_price
        )

        position.stop_update_count += 1
        position.trailing_active = True

        # ----------------------------------------------------
        # STOP R
        # ----------------------------------------------------

        initial_risk = (
            position.entry_price
            - position.initial_stop_price
        )

        if initial_risk > 0:

            position.stop_r = (
                new_stop_price
                - position.entry_price
            ) / initial_risk

        return True

    # ========================================================
    # CLOSE POSITION
    # ========================================================

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_time,
        exit_reason: str,
    ):

        if symbol not in self.positions:

            raise ValueError(
                f"{symbol}: açık pozisyon bulunamadı."
            )

        position = (
            self.positions[symbol]
        )

        exit_price = float(
            exit_price
        )

        if exit_price <= 0:

            raise ValueError(
                f"{symbol}: exit_price > 0 olmalıdır."
            )

        # ----------------------------------------------------
        # GROSS P/L
        # ----------------------------------------------------

        gross_pnl = (
            exit_price
            - position.entry_price
        ) * position.quantity

        # ----------------------------------------------------
        # VALUES
        # ----------------------------------------------------

        entry_value = (
            position.entry_price
            * position.quantity
        )

        exit_value = (
            exit_price
            * position.quantity
        )

        # ----------------------------------------------------
        # COMMISSIONS
        # ----------------------------------------------------

        entry_commission = (
            entry_value
            * self.commission_pct
        )

        exit_commission = (
            exit_value
            * self.commission_pct
        )

        # ----------------------------------------------------
        # NET P/L
        # ----------------------------------------------------

        net_pnl = (
            gross_pnl
            - entry_commission
            - exit_commission
        )

        if entry_value > 0:

            pnl_pct = (
                net_pnl
                / entry_value
            )

        else:

            pnl_pct = 0.0

        # ----------------------------------------------------
        # HOLDING TIME
        # ----------------------------------------------------

        holding_seconds = None

        try:

            holding_seconds = (
                exit_time
                - position.entry_time
            ).total_seconds()

        except (
            AttributeError,
            TypeError,
        ):

            pass

        holding_minutes = (
            holding_seconds / 60.0
            if holding_seconds is not None
            else None
        )

        # ----------------------------------------------------
        # RETURN CASH
        # ----------------------------------------------------

        self.cash += (
            exit_value
            - exit_commission
        )

        # ----------------------------------------------------
        # TRADE METRICS
        # ----------------------------------------------------

        trade_metrics = dict(
            position.entry_metrics
        )

        trade_metrics.update({

            "holding_minutes": (
                holding_minutes
            ),

            "gross_pnl": (
                gross_pnl
            ),

            "entry_value": (
                entry_value
            ),

            "exit_value": (
                exit_value
            ),

            "return_on_entry_pct": (
                pnl_pct * 100
            ),

            # ------------------------------------------------
            # V2 TRADE MANAGEMENT METADATA
            # ------------------------------------------------

            "initial_stop_price": (
                position.initial_stop_price
            ),

            "final_stop_price": (
                position.stop_price
            ),

            "highest_price": (
                position.highest_price
            ),

            "final_r": (
                position.current_r
            ),

            "stop_r": (
                position.stop_r
            ),

            "trailing_active": (
                position.trailing_active
            ),

            "stop_update_count": (
                position.stop_update_count
            ),
        })

        # ----------------------------------------------------
        # CLOSED TRADE
        # ----------------------------------------------------

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

            entry_commission=(
                entry_commission
            ),

            exit_commission=(
                exit_commission
            ),

            slippage_cost=0.0,

            entry_signal_score=(
                position.entry_signal_score
            ),

            entry_metrics=trade_metrics,
        )

        self.closed_trades.append(
            trade
        )

        del self.positions[symbol]

        return trade

    # ========================================================
    # EQUITY SNAPSHOT
    # ========================================================

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

        self.update_unrealized_pnl(
            prices
        )

        equity = (
            self.calculate_equity(
                prices
            )
        )

        self.equity_curve.append({

            "timestamp": timestamp,

            "equity": float(
                equity
            ),

            "cash": float(
                self.cash
            ),

            "open_positions": len(
                self.positions
            ),

            "daily_start_equity": (
                float(daily_start_equity)
                if daily_start_equity is not None
                else None
            ),

            "daily_return_pct": (
                float(daily_return_pct)
                if daily_return_pct is not None
                else None
            ),

            "daily_loss_limit_hit": bool(
                daily_loss_limit_hit
            ),

            "daily_tp1_hit": bool(
                daily_tp1_hit
            ),

            "daily_tp2_hit": bool(
                daily_tp2_hit
            ),
        })