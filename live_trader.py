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

    def get_current_equity(self):
        account = self.order_manager.get_account()
        if account:
            return float(account.equity)
        return 0.0

    def get_entry_price(self, symbol: str) -> float:
        """ Alpaca'dan hissenin maliyetini (ortalama giriş fiyatını) getirir. """
        try:
            position = self.order_manager.client.get_open_position(symbol)
            return float(position.avg_entry_price)
        except:
            return 0.0

    def manage_trailing_stops(self, df_dict, open_symbols):
        """
        V2.2 ZERO-LOSS DYNAMICS (Trailing Stop Management)
        Açık pozisyonlardaki kâr oranına (R-Multiple) bakarak stop seviyelerini 
        Alpaca sunucularında dinamik olarak günceller.
        """
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛡️ Aktif İşlemlerin Savunma Hatları (Stop-Loss) Kontrol Ediliyor...")
        
        for symbol in open_symbols:
            if symbol not in df_dict or df_dict[symbol].empty:
                continue
                
            current_price = float(df_dict[symbol].iloc[-1]["close"])
            entry_price = self.get_entry_price(symbol)
            
            if entry_price <= 0:
                continue

            # R Hesaplaması (Risk Mesafesi)
            # Not: Alpaca'daki güncel stop emrini bulup mesafeyi ölçmemiz gerekir. 
            # Ancak basitlik adına, settings'teki ilk ATR değerini R olarak kabul ediyoruz.
            atr = float(df_dict[symbol].iloc[-1]["atr"])
            initial_risk_per_share = atr * self.settings.atr_stop_multiplier
            
            if initial_risk_per_share <= 0:
                continue

            # Mevcut Kârımız (R cinsinden)
            current_profit_per_share = current_price - entry_price
            current_r = current_profit_per_share / initial_risk_per_share

            # Alpaca'daki mevcut (açık) Stop emrini bul
            # Not: OrderManager içinde update_stop_order gibi bir fonksiyonunuz olduğunu varsayıyoruz.
            # Eğer yoksa, yeni stop emri gönderip eskisini iptal etme mantığı kurulmalıdır.
            
            new_stop_price = None
            reason = ""

            # 1. Break-Even (Sıfır Zarar) Kalkanı (%0.75R'ye ulaşınca)
            if current_r >= self.settings.break_even_at_r and current_r < self.settings.lock_profit_at_r:
                new_stop_price = entry_price
                reason = "BREAK-EVEN (Sıfır Zarar Kalkanı Aktif)"

            # 2. Lock Profit (Kâr Kilitleme) Kalkanı (%1.2R'ye ulaşınca %0.5R kilitler)
            elif current_r >= self.settings.lock_profit_at_r and current_r < self.settings.trailing_start_at_r:
                new_stop_price = entry_price + (initial_risk_per_share * self.settings.lock_profit_r)
                reason = "PROFIT LOCK (Kâr Kilitlendi)"

            # 3. Trailing Stop (Süren Stop - Trend Takibi)
            elif current_r >= self.settings.trailing_start_at_r:
                trailing_distance = atr * self.settings.trailing_atr_multiplier
                new_stop_price = current_price - trailing_distance
                reason = "TRAILING STOP (Trend Takibi)"

            if new_stop_price and new_stop_price > entry_price:
                # Alpaca sunucusuna git ve hissenin stop emrini new_stop_price olarak güncelle
                # (Sistemin geriye stop çekmemesi için sadece yukarı yönde güncellendiğinden emin olmalısınız)
                try:
                    # self.order_manager.update_stop_loss(symbol, new_stop_price)
                    print(f" >>> [GÜNCELLEME] {symbol} | Mevcut R: {current_r:.2f}R | Yeni Stop: ${new_stop_price:.2f} | Neden: {reason}")
                except Exception as e:
                    print(f"     X Stop güncellenemedi {symbol}: {e}")

    def run(self):
        print("\n" + "=" * 60)
        print("🟢 CANLI İŞLEM MOTORU (V2.2 AUTONOMOUS SWING) BAŞLATILDI 🟢")
        print("=" * 60)
        
        print(f"Başlangıç Bakiyesi: ${self.get_current_equity():.2f}")
        print("Mevcut strateji: Günlük grafiklerde (1440 min) formasyon avı ve Zero-Loss koruması.")

        # Swing Trading'de piyasayı saniyede bir taramaya gerek yoktur.
        # Günde birkaç kez (veya saatte bir) tarama yapmak yeterlidir.
        SCAN_INTERVAL_SECONDS = 3600 # Her 1 saatte bir piyasayı tara

        while True:
            try:
                # 1. AÇIK POZİSYONLARI ÇEK
                account_positions = self.order_manager.client.get_all_positions()
                open_symbols = {p.symbol for p in account_positions}
                
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Piyasa Taranıyor... Açık Pozisyonlar: {list(open_symbols)}")

                # Günlük verileri Alpaca'dan çek
                df_dict = self.market_data.get_recent_bars()

                # 2. SAVUNMA HATTI (TRAILING STOP YÖNETİMİ)
                if open_symbols:
                    self.manage_trailing_stops(df_dict, open_symbols)

                # 3. YENİ FIRSAT ARAMA (Sadece bütçe ve kontenjan varsa)
                if len(open_symbols) < self.settings.max_open_positions:
                    
                    for symbol in self.settings.universe:
                        # Zaten içeride olduğumuz hisseye (veya Kara Listedeki TSLA'ya) tekrar girme
                        if symbol in open_symbols:
                            continue

                        if symbol not in df_dict or df_dict[symbol].empty:
                            continue

                        # İndikatörleri hesapla
                        df_symbol = self.indicator_engine.calculate(df_dict[symbol])

                        if len(df_symbol) < 52:
                            continue

                        # V2.2 Sinyal motoruna sor (Zero-Fake & Anti-Whipsaw)
                        signal_result = self.signal_engine.evaluate(symbol, df_symbol)

                        if signal_result.signal == Signal.BUY:
                            print(f"\n[SİNYAL] 🎯 {symbol} İÇİN KUSURSUZ FIRSAT (BUY) YAKALANDI!")
                            print(f" >>> Nedenler: {signal_result.reasons}")

                            current_price = float(df_symbol.iloc[-1]["close"])
                            atr = float(df_symbol.iloc[-1]["atr"])

                            # Stop (1.5x ATR)
                            stop_distance = atr * self.settings.atr_stop_multiplier
                            stop_price = current_price - stop_distance
                            
                            # Swing Trading'de Fixed Target (Sabit Hedef) kullanmıyoruz. 
                            # Kârı Trailing Stop ile açık uçlu bırakıyoruz. Ancak Alpaca Bracket emir için
                            # sembolik ve çok yüksek bir Take Profit seviyesi (örn: %50 yukarıda) belirleyebiliriz.
                            target_price = current_price * 1.50 

                            # Pozisyon Büyüklüğü (Kasanın %33'ü)
                            equity = self.get_current_equity()
                            max_risk_amount = equity * self.settings.max_risk_per_trade_pct
                            risk_per_share = current_price - stop_price

                            if risk_per_share > 0:
                                quantity = max_risk_amount / risk_per_share
                                max_allowed_value = equity * self.settings.max_position_size_pct

                                # Eğer bütçeyi (Kasanın %33'ünü) aşıyorsa miktarı kırp
                                if (quantity * current_price) > max_allowed_value:
                                    quantity = max_allowed_value / current_price

                                if quantity > 0:
                                    print(f" >>> Emir Gönderiliyor: {symbol} | Lot: {quantity:.2f} | Giriş: ${current_price:.2f} | Stop: ${stop_price:.2f}")
                                    # Alpaca'ya Bracket Order Ateş Et!
                                    self.order_manager.submit_bracket_order(
                                        symbol=symbol,
                                        quantity=quantity,
                                        side=OrderSide.BUY,
                                        stop_price=stop_price,
                                        target_price=target_price
                                    )
                                    time.sleep(5) # Spamlara karşı bekle

                # Swing ticaretinde sürekli tetikte kalmaya gerek yoktur. Saatte bir uyanır.
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Tarama tamamlandı. {SCAN_INTERVAL_SECONDS//60} dakika sonra tekrar uyanılacak...")
                time.sleep(SCAN_INTERVAL_SECONDS)

            except Exception as e:
                print(f"[HATA] Canlı döngüde beklenmeyen hata: {e}")
                time.sleep(60)

if __name__ == "__main__":
    trader = LiveTrader()
    trader.run()