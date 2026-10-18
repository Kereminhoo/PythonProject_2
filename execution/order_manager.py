from alpaca.trading.client import TradingClient
from alpaca.trading.enums import (
    OrderClass,
    OrderSide,
    TimeInForce,
)
from alpaca.trading.requests import (
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)

class OrderManager:

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

    # ========================================================
    # ACCOUNT
    # ========================================================

    def get_account(self):

        try:

            return (
                self.client
                .get_account()
            )

        except Exception as error:

            print(
                f"[ERROR] "
                f"Hesap bilgileri alınamadı: "
                f"{error}"
            )

            return None

    # ========================================================
    # POSITIONS
    # ========================================================

    def get_all_positions(self):

        try:

            return (
                self.client
                .get_all_positions()
            )

        except Exception as error:

            print(
                f"[ERROR] "
                f"Pozisyonlar alınamadı: "
                f"{error}"
            )

            return []

    # ========================================================
    # OPEN ORDERS
    # ========================================================

    def get_open_orders(self):

        try:

            return (
                self.client
                .get_orders()
            )

        except Exception as error:

            print(
                f"[ERROR] "
                f"Açık emirler alınamadı: "
                f"{error}"
            )

            return []

    # ========================================================
    # BRACKET ORDER
    # ========================================================

    def submit_bracket_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        stop_price: float,
        target_price: float,
    ):

        try:

            qty = round(
                float(quantity),
                4,
            )

            stop_px = round(
                float(stop_price),
                2,
            )

            target_px = round(
                float(target_price),
                2,
            )

            if qty <= 0:

                print(
                    f"[WARNING] "
                    f"{symbol} için "
                    f"geçersiz miktar: {qty}"
                )

                return None

            if stop_px <= 0:

                print(
                    f"[WARNING] "
                    f"{symbol} için "
                    f"geçersiz stop: {stop_px}"
                )

                return None

            if target_px <= 0:

                print(
                    f"[WARNING] "
                    f"{symbol} için "
                    f"geçersiz hedef: {target_px}"
                )

                return None

            request = (
                MarketOrderRequest(

                    symbol=symbol,

                    qty=qty,

                    side=side,

                    time_in_force=(
                        TimeInForce.GTC
                    ),

                    order_class=(
                        OrderClass.BRACKET
                    ),

                    take_profit=(
                        TakeProfitRequest(
                            limit_price=target_px
                        )
                    ),

                    stop_loss=(
                        StopLossRequest(
                            stop_price=stop_px
                        )
                    ),
                )
            )

            order = (
                self.client.submit_order(
                    order_data=request
                )
            )

            print(
                f"[EXECUTION] "
                f"{symbol} BRACKET ORDER gönderildi."
            )

            print(
                f"   -> Side      : "
                f"{side.name}"
            )

            print(
                f"   -> Quantity  : "
                f"{qty}"
            )

            print(
                f"   -> Stop      : "
                f"${stop_px:.2f}"
            )

            print(
                f"   -> Target    : "
                f"${target_px:.2f}"
            )

            return order

        except Exception as error:

            print(
                f"[ERROR] "
                f"{symbol} bracket order "
                f"gönderilemedi: {error}"
            )

            return None

    # ========================================================
    # CLOSE SYMBOL
    # ========================================================

    def close_position(
        self,
        symbol: str,
    ):

        try:

            print(
                f"[EXECUTION] "
                f"{symbol} pozisyonu kapatılıyor..."
            )

            return (
                self.client
                .close_position(
                    symbol
                )
            )

        except Exception as error:

            print(
                f"[ERROR] "
                f"{symbol} pozisyonu kapatılamadı: "
                f"{error}"
            )

            return None

    # ========================================================
    # CLOSE ALL
    # ========================================================

    def close_all_positions(self):

        try:

            print(
                "[EXECUTION] "
                "Tüm pozisyonlar kapatılıyor..."
            )

            return (
                self.client
                .close_all_positions(
                    cancel_orders=True
                )
            )

        except Exception as error:

            print(
                f"[ERROR] "
                f"Pozisyonlar kapatılamadı: "
                f"{error}"
            )

            return None

    # ========================================================
    # CANCEL ALL ORDERS
    # ========================================================

    def cancel_all_orders(self):

        try:

            print(
                "[EXECUTION] "
                "Tüm bekleyen emirler iptal ediliyor..."
            )

            return (
                self.client
                .cancel_orders()
            )

        except Exception as error:

            print(
                f"[ERROR] "
                f"Emirler iptal edilemedi: "
                f"{error}"
            )

            return None

    # ========================================================
    # GET ORDER
    # ========================================================

    def get_order(
        self,
        order_id,
    ):

        try:

            return (
                self.client
                .get_order_by_id(
                    order_id
                )
            )

        except Exception as error:

            print(
                f"[ERROR] "
                f"Order alınamadı: "
                f"{error}"
            )

            return None