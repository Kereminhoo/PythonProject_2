from dataclasses import dataclass
from risk.position_sizer import PositionSizer

# ============================================================
# RISK DECISION
# ============================================================
@dataclass
class RiskDecision:
    approved: bool
    reason: str

    max_risk_amount: float
    current_daily_pnl_pct: float

    current_open_risk: float = 0.0
    projected_open_risk: float = 0.0
    max_total_open_risk: float = 0.0

    new_trade_risk: float = 0.0

# ============================================================
# RISK MANAGER
# ============================================================
class RiskManager:

    def __init__(
        self,
        trading_client,
        settings,
    ):

        self.trading_client = (
            trading_client
        )

        self.settings = settings

        self.position_sizer = (
            PositionSizer(
                settings
            )
        )

        # ----------------------------------------------------
        # LOCAL POSITION RISK REGISTRY
        # ----------------------------------------------------

        self.position_risk_registry = {}

    # ========================================================
    # ACCOUNT
    # ========================================================

    def get_account(self):

        if self.trading_client is None:

            raise ValueError(
                "Trading client bulunmuyor."
            )

        return (
            self.trading_client
            .get_account()
        )

    # ========================================================
    # EQUITY
    # ========================================================

    def get_equity(self) -> float:

        account = (
            self.get_account()
        )

        return float(
            account.equity
        )

    # ========================================================
    # DAILY P/L
    # ========================================================

    def get_daily_pnl_pct(self) -> float:

        account = (
            self.get_account()
        )

        equity = float(
            account.equity
        )

        last_equity = float(
            account.last_equity
        )

        if last_equity <= 0:

            return 0.0

        return (
            equity
            - last_equity
        ) / last_equity

    # ========================================================
    # MAX RISK PER TRADE
    # ========================================================

    def get_max_risk_amount(
        self,
        equity: float | None = None,
    ) -> float:

        if equity is None:

            equity = self.get_equity()

        equity = float(
            equity
        )

        if equity <= 0:

            return 0.0

        risk_pct = float(
            self.settings.max_risk_per_trade_pct
        )

        if risk_pct <= 0:

            return 0.0

        return (
            equity
            * risk_pct
        )

    # ========================================================
    # RISK PER SHARE
    # ========================================================

    @staticmethod
    def calculate_risk_per_share(
        entry_price: float,
        stop_price: float,
    ) -> float:

        entry_price = float(
            entry_price
        )

        stop_price = float(
            stop_price
        )

        if entry_price <= 0:

            return 0.0

        if stop_price <= 0:

            return 0.0

        risk_per_share = (
            entry_price
            - stop_price
        )

        if risk_per_share <= 0:

            return 0.0

        return risk_per_share

    # ========================================================
    # LEGACY POSITION SIZE API
    # ========================================================

    def calculate_position_size(
        self,
        equity: float,
        entry_price: float,
        stop_price: float,
    ) -> float:

        equity = float(
            equity
        )

        entry_price = float(
            entry_price
        )

        stop_price = float(
            stop_price
        )

        risk_per_share = (
            self.calculate_risk_per_share(
                entry_price,
                stop_price,
            )
        )

        if risk_per_share <= 0:

            return 0.0

        max_risk_amount = (
            self.get_max_risk_amount(
                equity
            )
        )

        if max_risk_amount <= 0:

            return 0.0

        return max(
            max_risk_amount
            / risk_per_share,
            0.0,
        )

    # ========================================================
    # CENTRAL POSITION SIZING
    # ========================================================

    def calculate_position(
        self,
        symbol: str,
        entry_price: float,
        atr: float,
        equity: float,
        available_cash: float | None = None,
    ):

        return (
            self.position_sizer.calculate(

                symbol=symbol,

                entry_price=entry_price,

                atr=atr,

                equity=equity,

                available_cash=available_cash,
            )
        )

    # ========================================================
    # POSITION VALUE LIMIT
    # ========================================================

    def apply_position_value_limit(
        self,
        quantity: float,
        entry_price: float,
        equity: float,
    ) -> float:

        quantity = float(
            quantity
        )

        entry_price = float(
            entry_price
        )

        equity = float(
            equity
        )

        if quantity <= 0:

            return 0.0

        if entry_price <= 0:

            return 0.0

        if equity <= 0:

            return 0.0

        if hasattr(
            self.settings,
            "max_position_size_pct",
        ):
            max_position_pct = float(
                self.settings
                .max_position_size_pct
            )
        else:
            max_position_pct = float(
                getattr(
                    self.settings,
                    "max_position_pct",
                    0.0,
                )
            )

        if max_position_pct <= 0:

            return 0.0

        max_position_value = (
            equity
            * max_position_pct
        )

        max_quantity = (
            max_position_value
            / entry_price
        )

        return max(
            min(
                quantity,
                max_quantity,
            ),
            0.0,
        )

    # ========================================================
    # REGISTER POSITION RISK
    # ========================================================

    def register_position_risk(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        stop_price: float,
    ) -> None:

        quantity = float(
            quantity
        )

        entry_price = float(
            entry_price
        )

        stop_price = float(
            stop_price
        )

        if quantity <= 0:

            raise ValueError(
                "Quantity 0'dan büyük olmalıdır."
            )

        if entry_price <= 0:

            raise ValueError(
                "Entry price 0'dan büyük olmalıdır."
            )

        if stop_price <= 0:

            raise ValueError(
                "Stop price 0'dan büyük olmalıdır."
            )

        risk_per_share = (
            entry_price
            - stop_price
        )

        # This registry represents an already-open position.
        # Its stop may therefore be at break-even or above entry
        # after profit protection / trailing has activated.
        #
        # IMPORTANT:
        # New trades must NOT use this exception.
        # calculate_trade_risk() remains strict and rejects
        # stop >= entry by returning infinity.
        risk_amount = max(
            quantity
            * risk_per_share,
            0.0,
        )

        self.position_risk_registry[
            symbol
        ] = {

            "quantity":
                quantity,

            "entry_price":
                entry_price,

            "stop_price":
                stop_price,

            "risk_amount":
                risk_amount,
        }

    # ========================================================
    # UNREGISTER
    # ========================================================

    def unregister_position(
        self,
        symbol: str,
    ) -> None:

        self.position_risk_registry.pop(
            symbol,
            None,
        )

    # ========================================================
    # TOTAL OPEN RISK
    # ========================================================

    def calculate_total_open_risk(
        self,
    ) -> float:

        total_risk = 0.0

        for position_data in (
            self.position_risk_registry.values()
        ):

            total_risk += float(
                position_data[
                    "risk_amount"
                ]
            )

        return float(
            total_risk
        )

    # ========================================================
    # TOTAL OPEN RISK %
    # ========================================================

    def calculate_total_open_risk_pct(
        self,
        equity: float | None = None,
    ) -> float:

        if equity is None:

            equity = self.get_equity()

        equity = float(
            equity
        )

        if equity <= 0:

            return 0.0

        return (
            self.calculate_total_open_risk()
            / equity
        )

    # ========================================================
    # MAX TOTAL OPEN RISK
    # ========================================================

    def get_max_total_open_risk_amount(
        self,
        equity: float | None = None,
    ) -> float:

        if equity is None:

            equity = self.get_equity()

        equity = float(
            equity
        )

        if equity <= 0:

            return 0.0

        if hasattr(
            self.settings,
            "max_total_open_risk_pct",
        ):

            total_risk_pct = float(
                self.settings
                .max_total_open_risk_pct
            )

        else:

            total_risk_pct = (
                float(
                    self.settings
                    .max_risk_per_trade_pct
                )
                *
                int(
                    self.get_effective_max_open_positions()
                )
            )

        if total_risk_pct <= 0:

            return 0.0

        return (
            equity
            * total_risk_pct
        )

    # ========================================================
    # NEW TRADE RISK
    # ========================================================

    def calculate_trade_risk(
        self,
        quantity: float,
        entry_price: float,
        stop_price: float,
    ) -> float:

        quantity = float(
            quantity
        )

        risk_per_share = (
            self.calculate_risk_per_share(
                entry_price,
                stop_price,
            )
        )

        if quantity <= 0:

            return float("inf")

        if risk_per_share <= 0:

            return float("inf")

        return (
            quantity
            * risk_per_share
        )

    # ========================================================
    # NEW TRADE TOTAL RISK
    # ========================================================

    def calculate_total_risk_with_trade(
        self,
        quantity: float,
        entry_price: float,
        stop_price: float,
    ) -> float:

        new_trade_risk = (
            self.calculate_trade_risk(
                quantity,
                entry_price,
                stop_price,
            )
        )

        if new_trade_risk == float("inf"):

            return float("inf")

        return (
            self.calculate_total_open_risk()
            + new_trade_risk
        )

    # ========================================================
    # TOTAL RISK CHECK
    # ========================================================

    def total_open_risk_limit_reached(
        self,
        additional_risk: float = 0.0,
        equity: float | None = None,
    ) -> bool:

        if equity is None:

            equity = self.get_equity()

        max_total_risk = (
            self.get_max_total_open_risk_amount(
                equity
            )
        )

        projected_risk = (
            self.calculate_total_open_risk()
            + float(additional_risk)
        )

        return (
            projected_risk
            > max_total_risk
        )

    # ========================================================
    # DAILY LOSS LIMIT
    # ========================================================

    def daily_loss_limit_reached(
        self,
    ):

        daily_pnl_pct = (
            self.get_daily_pnl_pct()
        )

        return (
            daily_pnl_pct
            <= -float(
                self.settings.max_daily_loss_pct
            )
        )

    # ========================================================
    # EFFECTIVE OPEN POSITION LIMIT
    # ========================================================

    def get_effective_max_open_positions(
        self,
    ) -> int:

        max_positions = int(
            getattr(
                self.settings,
                "max_open_positions",
                0,
            )
        )

        if max_positions < 0:
            max_positions = 0

        micro_enabled = bool(
            getattr(
                self.settings,
                "micro_account_mode",
                False,
            )
        )

        if not micro_enabled:
            return max_positions

        micro_limit = int(
            getattr(
                self.settings,
                "micro_max_open_positions",
                max_positions,
            )
        )

        if micro_limit < 0:
            micro_limit = 0

        return min(
            max_positions,
            micro_limit,
        )

    # ========================================================
    # OPEN POSITION COUNT
    # ========================================================

    def get_open_position_count(
        self,
    ):

        if self.trading_client is not None:

            positions = (
                self.trading_client
                .get_all_positions()
            )

            return len(
                positions
            )

        return len(
            self.position_risk_registry
        )

    # ========================================================
    # EXISTING SYMBOLS
    # ========================================================

    def get_existing_symbols(
        self,
    ):

        if self.trading_client is not None:

            positions = (
                self.trading_client
                .get_all_positions()
            )

            return {
                position.symbol
                for position in positions
            }

        return set(
            self.position_risk_registry.keys()
        )

    # ========================================================
    # CENTRAL POSITION APPROVAL
    # ========================================================

    def approve_position(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        stop_price: float,
        equity: float | None = None,
        daily_pnl_pct: float | None = None,
    ) -> RiskDecision:

        if equity is None:

            equity = self.get_equity()

        equity = float(
            equity
        )

        if daily_pnl_pct is None:

            daily_pnl_pct = (
                self.get_daily_pnl_pct()
            )

        daily_pnl_pct = float(
            daily_pnl_pct
        )

        max_risk = (
            self.get_max_risk_amount(
                equity
            )
        )

        current_open_risk = (
            self.calculate_total_open_risk()
        )

        max_total_risk = (
            self.get_max_total_open_risk_amount(
                equity
            )
        )

        new_trade_risk = (
            self.calculate_trade_risk(
                quantity,
                entry_price,
                stop_price,
            )
        )

        projected_open_risk = (
            current_open_risk
            + new_trade_risk
        )

        # ----------------------------------------------------
        # EQUITY
        # ----------------------------------------------------

        if equity <= 0:

            return RiskDecision(

                approved=False,

                reason="Invalid account equity.",

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        # ----------------------------------------------------
        # QUANTITY
        # ----------------------------------------------------

        if quantity <= 0:

            return RiskDecision(

                approved=False,

                reason="Invalid position quantity.",

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        # ----------------------------------------------------
        # NEW TRADE STOP VALIDATION
        # ----------------------------------------------------

        if entry_price <= 0:

            return RiskDecision(

                approved=False,

                reason="Invalid entry price.",

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        if stop_price <= 0:

            return RiskDecision(

                approved=False,

                reason="Invalid stop price.",

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        if stop_price >= entry_price:

            return RiskDecision(

                approved=False,

                reason=(
                    "Stop price must be below entry price "
                    "for a new trade."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        # ----------------------------------------------------
        # DUPLICATE
        # ----------------------------------------------------

        if symbol in self.get_existing_symbols():

            return RiskDecision(

                approved=False,

                reason=(
                    f"{symbol} already exists "
                    "in portfolio."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        # ----------------------------------------------------
        # DAILY LOSS
        # ----------------------------------------------------

        if daily_pnl_pct <= -float(
            self.settings.max_daily_loss_pct
        ):

            return RiskDecision(

                approved=False,

                reason=(
                    "Daily loss limit reached."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        # ----------------------------------------------------
        # INDIVIDUAL TRADE RISK
        # ----------------------------------------------------

        if (
            new_trade_risk
            > max_risk
        ):

            return RiskDecision(

                approved=False,

                reason=(
                    "Maximum risk per trade exceeded."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        # ----------------------------------------------------
        # POSITION COUNT
        # ----------------------------------------------------

        position_count = (
            self.get_open_position_count()
        )

        if (
            position_count
            >= self.get_effective_max_open_positions()
        ):

            return RiskDecision(

                approved=False,

                reason=(
                    "Maximum open positions reached."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        # ----------------------------------------------------
        # TOTAL RISK
        # ----------------------------------------------------

        if (
            projected_open_risk
            > max_total_risk
        ):

            return RiskDecision(

                approved=False,

                reason=(
                    "Maximum total open risk exceeded."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=projected_open_risk,

                max_total_open_risk=max_total_risk,

                new_trade_risk=new_trade_risk,
            )

        # ----------------------------------------------------
        # APPROVED
        # ----------------------------------------------------

        return RiskDecision(

            approved=True,

            reason="Risk checks passed.",

            max_risk_amount=max_risk,

            current_daily_pnl_pct=daily_pnl_pct,

            current_open_risk=current_open_risk,

            projected_open_risk=projected_open_risk,

            max_total_open_risk=max_total_risk,

            new_trade_risk=new_trade_risk,
        )

    # ========================================================
    # LEGACY / LIVE TRADE APPROVAL
    # ========================================================

    def approve_trade(
        self,
        symbol,
    ) -> RiskDecision:

        daily_pnl_pct = (
            self.get_daily_pnl_pct()
        )

        equity = (
            self.get_equity()
        )

        max_risk = (
            self.get_max_risk_amount(
                equity
            )
        )

        current_open_risk = (
            self.calculate_total_open_risk()
        )

        max_total_risk = (
            self.get_max_total_open_risk_amount(
                equity
            )
        )

        # ----------------------------------------------------
        # EQUITY
        # ----------------------------------------------------

        if equity <= 0:

            return RiskDecision(

                approved=False,

                reason="Invalid account equity.",

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=current_open_risk,

                max_total_open_risk=max_total_risk,
            )

        # ----------------------------------------------------
        # DAILY LOSS
        # ----------------------------------------------------

        if self.daily_loss_limit_reached():

            return RiskDecision(

                approved=False,

                reason=(
                    "Daily loss limit reached."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=current_open_risk,

                max_total_open_risk=max_total_risk,
            )

        # ----------------------------------------------------
        # POSITION COUNT
        # ----------------------------------------------------

        if (
            self.get_open_position_count()
            >= self.get_effective_max_open_positions()
        ):

            return RiskDecision(

                approved=False,

                reason=(
                    "Maximum open positions reached."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=current_open_risk,

                max_total_open_risk=max_total_risk,
            )

        # ----------------------------------------------------
        # DUPLICATE
        # ----------------------------------------------------

        if (
            symbol
            in self.get_existing_symbols()
        ):

            return RiskDecision(

                approved=False,

                reason=(
                    f"{symbol} already exists "
                    "in portfolio."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=current_open_risk,

                max_total_open_risk=max_total_risk,
            )

        # ----------------------------------------------------
        # TOTAL RISK
        # ----------------------------------------------------

        if (
            current_open_risk
            > max_total_risk
        ):

            return RiskDecision(

                approved=False,

                reason=(
                    "Maximum total open risk exceeded."
                ),

                max_risk_amount=max_risk,

                current_daily_pnl_pct=daily_pnl_pct,

                current_open_risk=current_open_risk,

                projected_open_risk=current_open_risk,

                max_total_open_risk=max_total_risk,
            )

        # ----------------------------------------------------
        # APPROVED
        # ----------------------------------------------------

        return RiskDecision(

            approved=True,

            reason="Risk checks passed.",

            max_risk_amount=max_risk,

            current_daily_pnl_pct=daily_pnl_pct,

            current_open_risk=current_open_risk,

            projected_open_risk=current_open_risk,

            max_total_open_risk=max_total_risk,
        )
