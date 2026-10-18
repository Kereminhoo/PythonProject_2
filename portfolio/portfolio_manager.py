from dataclasses import dataclass
from typing import Dict, List, Optional
from alpaca.trading.client import TradingClient

# ============================================================
# PORTFOLIO POSITION
# ============================================================
@dataclass
class PortfolioPosition:
    symbol: str
    quantity: float
    entry_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    side: str

# ============================================================
# PORTFOLIO SNAPSHOT
# ============================================================
@dataclass
class PortfolioSnapshot:
    equity: float
    cash: float
    buying_power: float
    market_value: float
    total_unrealized_pnl: float
    open_positions: int
    positions: Dict[str, PortfolioPosition]

# ============================================================
# PORTFOLIO MANAGER
# ============================================================
class PortfolioManager:

    def __init__(
        self,
        settings,
    ):

        self.settings = settings

        self.client = TradingClient(

            api_key=(
                settings.alpaca_api_key
            ),

            secret_key=(
                settings.alpaca_secret_key
            ),

            paper=(
                settings.paper_trading
            ),
        )

        self._snapshot = None

    # ========================================================
    # ACCOUNT
    # ========================================================

    def get_account(self):

        return (
            self.client
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
    # CASH
    # ========================================================

    def get_cash(self) -> float:

        account = (
            self.get_account()
        )

        return float(
            account.cash
        )

    # ========================================================
    # BUYING POWER
    # ========================================================

    def get_buying_power(self) -> float:

        account = (
            self.get_account()
        )

        return float(
            account.buying_power
        )

    # ========================================================
    # POSITIONS
    # ========================================================

    def get_positions(self):

        return (
            self.client
            .get_all_positions()
        )

    # ========================================================
    # POSITION MAP
    # ========================================================

    def get_position_map(
        self,
    ) -> Dict[str, PortfolioPosition]:

        positions = (
            self.get_positions()
        )

        result = {}

        for position in positions:

            symbol = (
                str(position.symbol)
            )

            quantity = float(
                position.qty
            )

            entry_price = float(
                position.avg_entry_price
            )

            market_value = float(
                position.market_value
            )

            unrealized_pnl = float(
                position.unrealized_pl
            )

            unrealized_pnl_pct = float(
                position.unrealized_plpc
            )

            side = str(
                position.side
            )

            result[symbol] = (
                PortfolioPosition(

                    symbol=symbol,

                    quantity=quantity,

                    entry_price=entry_price,

                    market_value=market_value,

                    unrealized_pnl=(
                        unrealized_pnl
                    ),

                    unrealized_pnl_pct=(
                        unrealized_pnl_pct
                    ),

                    side=side,
                )
            )

        return result

    # ========================================================
    # HAS POSITION
    # ========================================================

    def has_position(
        self,
        symbol: str,
    ) -> bool:

        return (
            symbol
            in self.get_position_map()
        )

    # ========================================================
    # GET POSITION
    # ========================================================

    def get_position(
        self,
        symbol: str,
    ) -> Optional[PortfolioPosition]:

        positions = (
            self.get_position_map()
        )

        return positions.get(
            symbol
        )

    # ========================================================
    # OPEN POSITION COUNT
    # ========================================================

    def get_open_position_count(
        self,
    ) -> int:

        return len(
            self.get_positions()
        )

    # ========================================================
    # MARKET VALUE
    # ========================================================

    def calculate_market_value(
        self,
    ) -> float:

        total = 0.0

        for position in (
            self.get_positions()
        ):

            total += abs(
                float(
                    position.market_value
                )
            )

        return total

    # ========================================================
    # TOTAL UNREALIZED P/L
    # ========================================================

    def calculate_total_unrealized_pnl(
        self,
    ) -> float:

        total = 0.0

        for position in (
            self.get_positions()
        ):

            total += float(
                position.unrealized_pl
            )

        return total

    # ========================================================
    # TOTAL EXPOSURE %
    # ========================================================

    def calculate_total_exposure_pct(
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

        market_value = (
            self.calculate_market_value()
        )

        return (
            market_value
            / equity
        )

    # ========================================================
    # SNAPSHOT
    # ========================================================

    def snapshot(
        self,
    ) -> PortfolioSnapshot:

        equity = (
            self.get_equity()
        )

        cash = (
            self.get_cash()
        )

        buying_power = (
            self.get_buying_power()
        )

        positions = (
            self.get_position_map()
        )

        market_value = (
            self.calculate_market_value()
        )

        total_unrealized_pnl = (
            self.calculate_total_unrealized_pnl()
        )

        snapshot = (
            PortfolioSnapshot(

                equity=equity,

                cash=cash,

                buying_power=buying_power,

                market_value=market_value,

                total_unrealized_pnl=(
                    total_unrealized_pnl
                ),

                open_positions=len(
                    positions
                ),

                positions=positions,
            )
        )

        self._snapshot = snapshot

        return snapshot

    # ========================================================
    # LAST SNAPSHOT
    # ========================================================

    def get_last_snapshot(
        self,
    ) -> Optional[PortfolioSnapshot]:

        return self._snapshot