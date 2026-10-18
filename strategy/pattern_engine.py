from dataclasses import dataclass
import pandas as pd

# ============================================================
# PATTERN RESULT
# ============================================================

@dataclass
class PatternResult:
    hammer: bool
    engulfing: bool
    bull_flag: bool
    
    # Formasyonların toplam bonus skoru
    score: float
    
    reason: str


# ============================================================
# PATTERN ENGINE
# ============================================================

class PatternEngine:
    """
    Mum formasyonlarını (Candlestick Patterns) ve 
    fiyat sıkışmalarını (Contraction/Flags) tespit eder.
    """

    def __init__(self, settings=None):
        self.settings = settings

    def evaluate(self, df: pd.DataFrame) -> PatternResult:
        if df is None or len(df) < 5:
            return PatternResult(
                hammer=False, 
                engulfing=False, 
                bull_flag=False, 
                score=0.0, 
                reason="Yeterli veri yok"
            )

        last = df.iloc[-1]
        prev = df.iloc[-2]

        score = 0.0
        reasons = []

        # ====================================================
        # 1. HAMMER (ÇEKİÇ) FORMASYONU
        # ====================================================
        # Gövde küçük olmalı, alt fitil gövdenin en az 2 katı olmalı, üst fitil çok küçük olmalı.
        
        body = abs(last['close'] - last['open'])
        candle_range = last['high'] - last['low']
        
        lower_wick = min(last['open'], last['close']) - last['low']
        upper_wick = last['high'] - max(last['open'], last['close'])

        is_hammer = False
        if candle_range > 0 and (body / candle_range) < 0.3:  # Gövde mumun %30'undan küçük
            if lower_wick > (2 * body) and upper_wick < body:
                is_hammer = True
                score += 15.0
                reasons.append("Çekiç (Hammer) Tespit Edildi")

        # ====================================================
        # 2. BULLISH ENGULFING (YUTAN BOĞA)
        # ====================================================
        # Önceki mum kırmızı, şu anki yeşil olmalı ve yeşil gövde kırmızıyı yutmalı.
        
        prev_body = abs(prev['close'] - prev['open'])
        is_prev_red = prev['close'] < prev['open']
        is_curr_green = last['close'] > last['open']

        is_engulfing = False
        if is_prev_red and is_curr_green:
            if last['close'] > prev['open'] and last['open'] < prev['close']:
                is_engulfing = True
                score += 20.0
                reasons.append("Yutan Boğa (Engulfing) Tespit Edildi")

        # ====================================================
        # 3. BULL FLAG / VCP (BOĞA BAYRAĞI / SIKIŞMA)
        # ====================================================
        # Son 3-5 mumda fiyat aralığı (volatilite) daralıyor olmalı (ATR'ye kıyasla).
        
        is_flag = False
        if 'atr' in df.columns and pd.notna(last['atr']):
            # Son 4 mumun fiyat aralıkları
            recent_ranges = df['high'].iloc[-4:] - df['low'].iloc[-4:]
            avg_recent_range = recent_ranges.mean()
            
            # Eğer son mumların ortalama boyutu ATR'nin (14 günlük oynaklığın) %70'inden küçükse, sıkışma vardır.
            if avg_recent_range < (last['atr'] * 0.70):
                # Sıkışma varken fiyat 5 gün öncesine göre yukarıdaysa bu bir Boğa Bayrağıdır
                if last['close'] > df['close'].iloc[-5]:
                    is_flag = True
                    score += 15.0
                    reasons.append("Boğa Bayrağı Sıkışması (Bull Flag) Tespit Edildi")

        reason_str = ", ".join(reasons) if reasons else "Formasyon Yok"

        return PatternResult(
            hammer=is_hammer,
            engulfing=is_engulfing,
            bull_flag=is_flag,
            score=score,
            reason=reason_str
        )