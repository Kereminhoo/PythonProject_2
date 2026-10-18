from dataclasses import dataclass


# ============================================================
# POSITION SIZE RESULT
# ============================================================

@dataclass
class PositionSize:

    symbol: str

    entry_price: float
    stop_price: float
    target_price: float

    stop_distance: float
    target_distance: float

    risk_amount: float

    quantity: float
    position_value: float

    risk_reward_ratio: float


# ============================================================
# POSITION SIZER
# ============================================================

class PositionSizer:

    def __init__(self, settings):

        self.settings = settings

    # ========================================================
    # MAX POSITION EXPOSURE
    # ========================================================

    def _get_max_position_pct(self) -> float:
        """
        Maksimum tek pozisyon exposure oranını döndürür.

        Örnek:

            0.25 = %25
            0.50 = %50
            1.00 = %100
        """

        if hasattr(
            self.settings,
            "max_position_size_pct"
        ):

            max_position_pct = float(
                self.settings.max_position_size_pct
            )

        elif hasattr(
            self.settings,
            "max_position_pct"
        ):

            max_position_pct = float(
                self.settings.max_position_pct
            )

        else:

            # Eski/uyumsuz settings objeleri için
            # güvenli varsayılan: %100
            max_position_pct = 1.0

        if max_position_pct <= 0:

            raise ValueError(
                "max_position_pct "
                "0'dan büyük olmalıdır."
            )

        return max_position_pct

    # ========================================================
    # CALCULATE
    # ========================================================

    def calculate(
        self,
        symbol: str,
        entry_price: float,
        atr: float,
        equity: float,
        available_cash: float | None = None
    ) -> PositionSize:

        entry_price = float(
            entry_price
        )

        atr = float(
            atr
        )

        equity = float(
            equity
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if entry_price <= 0:

            raise ValueError(
                f"{symbol}: "
                "Entry price 0'dan büyük olmalıdır."
            )

        if atr <= 0:

            raise ValueError(
                f"{symbol}: "
                "ATR 0'dan büyük olmalıdır."
            )

        if equity <= 0:

            raise ValueError(
                f"{symbol}: "
                "Equity 0'dan büyük olmalıdır."
            )

        # ----------------------------------------------------
        # RISK
        # ----------------------------------------------------

        risk_pct = float(
            self.settings.max_risk_per_trade_pct
        )

        if risk_pct <= 0:

            raise ValueError(
                f"{symbol}: "
                "max_risk_per_trade_pct "
                "0'dan büyük olmalıdır."
            )

        max_risk_amount = (
            equity * risk_pct
        )

        # ----------------------------------------------------
        # STOP DISTANCE
        # ----------------------------------------------------

        atr_multiplier = float(
            self.settings.atr_stop_multiplier
        )

        if atr_multiplier <= 0:

            raise ValueError(
                f"{symbol}: "
                "atr_stop_multiplier "
                "0'dan büyük olmalıdır."
            )

        stop_distance = (
            atr * atr_multiplier
        )

        if stop_distance <= 0:

            raise ValueError(
                f"{symbol}: "
                "Stop distance geçersiz."
            )

        # ----------------------------------------------------
        # STOP PRICE
        # ----------------------------------------------------

        stop_price = (
            entry_price
            - stop_distance
        )

        if stop_price <= 0:

            raise ValueError(
                f"{symbol}: "
                "Hesaplanan stop price geçersiz."
            )

        # ----------------------------------------------------
        # RISK-BASED QUANTITY
        # ----------------------------------------------------

        quantity_by_risk = (
            max_risk_amount
            / stop_distance
        )

        # ----------------------------------------------------
        # EXPOSURE LIMIT
        # ----------------------------------------------------

        max_position_pct = (
            self._get_max_position_pct()
        )

        max_position_value = (
            equity
            * max_position_pct
        )

        quantity_by_exposure = (
            max_position_value
            / entry_price
        )

        # ----------------------------------------------------
        # FINAL QUANTITY
        # ----------------------------------------------------

        quantity = min(
            quantity_by_risk,
            quantity_by_exposure
        )

        # ----------------------------------------------------
        # CASH LIMIT
        # ----------------------------------------------------

        if available_cash is not None:

            available_cash = float(
                available_cash
            )

            if available_cash <= 0:

                raise ValueError(
                    f"{symbol}: "
                    "Available cash "
                    "0'dan büyük olmalıdır."
                )

            quantity_by_cash = (
                available_cash
                / entry_price
            )

            quantity = min(
                quantity,
                quantity_by_cash
            )

        # ----------------------------------------------------
        # FINAL VALIDATION
        # ----------------------------------------------------

        if quantity <= 0:

            raise ValueError(
                f"{symbol}: "
                "Position quantity "
                "0 veya negatif."
            )

        # ----------------------------------------------------
        # POSITION VALUE
        # ----------------------------------------------------

        position_value = (
            quantity
            * entry_price
        )

        # ----------------------------------------------------
        # FINAL EXPOSURE SAFETY CHECK
        # ----------------------------------------------------

        if position_value > max_position_value:

            quantity = (
                max_position_value
                / entry_price
            )

            position_value = (
                quantity
                * entry_price
            )

        # ----------------------------------------------------
        # TARGET
        # ----------------------------------------------------

        risk_reward_ratio = float(
            self.settings.risk_reward_ratio
        )

        if risk_reward_ratio <= 0:

            raise ValueError(
                f"{symbol}: "
                "risk_reward_ratio "
                "0'dan büyük olmalıdır."
            )

        target_distance = (
            stop_distance
            * risk_reward_ratio
        )

        target_price = (
            entry_price
            + target_distance
        )

        # ----------------------------------------------------
        # ACTUAL RISK
        # ----------------------------------------------------

        actual_risk_amount = (
            quantity
            * stop_distance
        )

        return PositionSize(

            symbol=symbol,

            entry_price=entry_price,

            stop_price=stop_price,

            target_price=target_price,

            stop_distance=stop_distance,

            target_distance=target_distance,

            risk_amount=actual_risk_amount,

            quantity=quantity,

            position_value=position_value,

            risk_reward_ratio=(
                risk_reward_ratio
            )
        )