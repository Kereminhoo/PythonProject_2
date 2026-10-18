import time
import pandas as pd
from datetime import datetime, timezone

from config.settings import load_settings
from data.market_data import MarketData
from strategy.indicators import IndicatorEngine
from strategy.signal_engine import SignalEngine, Signal
from execution.order_manager import OrderManager
from alpaca.trading.enums import OrderSide


class LiveTrader:
    def __init__(self):
        print("Sistem bileşenleri yükleniyor...")
        self.settings = load_settings()
        self.market_data = MarketData(self.settings)
        self.indicator_engine = IndicatorEngine(self.settings)
        self.signal_engine = SignalEngine(self.settings)
        self.order_manager = OrderManager(self.settings)

        # Günlük takip değişkenleri
        self.daily_start_equity = None
        self.current_day = None
        self.daily_trading_done = False
        self.tp1_hit = False

    def get_current_equity(self):
        account = self.order_manager.get_account()
        if account:
            return float(account.equity)
        return 0.0

    def check_daily_targets(self):
        """
        Her döngüde kasayı kontrol eder. %1 vurulmuşsa şalteri indirir.
        """
        current_equity = self.get_current_equity()
        if current_equity <= 0 or self.daily_start_equity is None or self.daily_start_equity <= 0:
            return False

        daily_return = (current_equity / self.daily_start_equity) - 1

        # ŞALTER: TP2 Kontrolü (%1 Hedef)
        if daily_return >= self.settings.daily_tp2_pct and not self.daily_trading_done:
            print("\n" + "!" * 60)
            print(f"💰 GÜNLÜK HEDEF VURULDU! Kâr: %{daily_return * 100:.2f} 💰")
            print("!" * 60)
            self.order_manager.close_all_positions()
            self.order_manager.cancel_all_orders()
            self.daily_trading_done = True
            return True

        # GÜVENLİK AĞI: TP1 Kontrolü (%0.5 Koruma)
        if daily_return >= self.settings.daily_tp1_pct and not self.tp1_hit:
            print("\n" + "-" * 60)
            print(f"🛡️ TP1 GÜVENLİK AĞI (%0.5) AKTİF! Kâr: %{daily_return * 100:.2f} 🛡️")
            print("-" * 60)
            self.tp1_hit = True

        # STOP-LOSS: Günlük Maksimum Zarar
        if daily_return <= -self.settings.max_daily_loss_pct and not self.daily_trading_done:
            print("\n" + "!" * 60)
            print(f"🛑 GÜNLÜK ZARAR LİMİTİNE ULAŞILDI! Zarar: %{daily_return * 100:.2f} 🛑")
            print("!" * 60)
            self.order_manager.close_all_positions()
            self.order_manager.cancel_all_orders()
            self.daily_trading_done = True
            return True

        return False

    def reset_daily_state_if_needed(self):
        now = datetime.now(timezone.utc)
        today = now.date()

        if self.current_day != today:
            print(f"\n{'=' * 60}\nYENİ GÜN BAŞLIYOR: {today}\n{'=' * 60}")
            self.current_day = today
            self.daily_start_equity = self.get_current_equity()
            self.daily_trading_done = False
            self.tp1_hit = False
            print(f"Günlük Başlangıç Kasası: ${self.daily_start_equity:.2f}")
            print("============================================================")

    def run(self):
        print("\n" + "=" * 60)
        print("🟢 CANLI İŞLEM MOTORU (V1.1 SNIPER MODE) BAŞLATILDI 🟢")
        print("=" * 60)

        while True:
            try:
                self.reset_daily_state_if_needed()

                # 1. GÜNLÜK ŞALTER KONTROLÜ
                if self.daily_trading_done:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Günlük mesai bitti. Piyasa izlenmiyor, yeni gün bekleniyor...")
                    time.sleep(300)  # Mesai bittiyse 5 dakikada bir uyan (Gereksiz API yormamak için)
                    continue

                # Kasa %1 oldu mu diye her döngüde kontrol et
                if self.check_daily_targets():
                    continue

                # 2. AÇIK POZİSYONLARI ÇEK
                account_positions = self.order_manager.client.get_all_positions()
                open_symbols = {p.symbol for p in account_positions}

                # 3. YENİ FIRSAT ARAMA (Sadece TP1 vurulmadıysa ve boş kontenjan varsa)
                if not self.tp1_hit and len(open_symbols) < self.settings.max_open_positions:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Piyasa taranıyor... Açık Pozisyonlar: {list(open_symbols)}")

                    df_dict = self.market_data.get_recent_bars()

                    for symbol in self.settings.universe:
                        # Zaten içeride olduğumuz hisseye tekrar girme
                        if symbol in open_symbols:
                            continue

                        if symbol not in df_dict or df_dict[symbol].empty:
                            continue

                        # İndikatörleri hesapla
                        df_symbol = self.indicator_engine.calculate(df_dict[symbol])

                        if len(df_symbol) < 30:
                            continue

                        # Sinyal motoruna sor (Kesin Kurallar - Boolean)
                        signal_result = self.signal_engine.evaluate(symbol, df_symbol)

                        if signal_result.signal == Signal.BUY:
                            print(f"\n[SİNYAL] 🎯 {symbol} İÇİN KUSURSUZ FIRSAT (BUY) YAKALANDI!")

                            current_price = float(df_symbol.iloc[-1]["close"])
                            atr = float(df_symbol.iloc[-1]["atr"])

                            # Stop ve Hedef (2.0x ATR, 1:1 RR)
                            stop_distance = atr * self.settings.atr_stop_multiplier
                            stop_price = current_price - stop_distance
                            target_distance = stop_distance * self.settings.risk_reward_ratio
                            target_price = current_price + target_distance

                            # Pozisyon Büyüklüğü (4x Alım Gücü Destekli)
                            equity = self.get_current_equity()
                            max_risk_amount = equity * self.settings.max_risk_per_trade_pct
                            risk_per_share = current_price - stop_price

                            if risk_per_share > 0:
                                quantity = max_risk_amount / risk_per_share
                                max_allowed_value = equity * self.settings.max_position_size_pct

                                # Eğer bütçeyi (4x'i) aşıyorsa miktarı kırp
                                if (quantity * current_price) > max_allowed_value:
                                    quantity = max_allowed_value / current_price

                                if quantity > 0:
                                    # Alpaca'ya Ateş Et!
                                    self.order_manager.submit_bracket_order(
                                        symbol=symbol,
                                        quantity=quantity,
                                        side=OrderSide.BUY,
                                        stop_price=stop_price,
                                        target_price=target_price
                                    )
                                    # Ard arda emir fırlatmaması için 10 saniye bekle
                                    time.sleep(10)

                # 60 saniyede bir döngüyü tekrarla (Piyasayı sürekli izler, kasayı günceller)
                time.sleep(60)

            except Exception as e:
                print(f"[HATA] Canlı döngüde beklenmeyen hata: {e}")
                # Hata alırsak spam yapmamak için 60 saniye dinlendir
                time.sleep(60)


if __name__ == "__main__":
    trader = LiveTrader()
    trader.run()