class ChaosBrake:
    """Pure Chaos Risk Brake – 4 signals → Tier 0–3 (Green/Yellow/Orange/Red)"""
    @staticmethod
    def get_tier(algorithm) -> int:
        try:
            vix = algorithm.Securities["VIX"].Price
            vol_signal = 1 if vix > 20 else 0

            yield_10y = algorithm.Securities["^TNX"].Price / 100
            yield_2y  = algorithm.Securities["^IRX"].Price / 100
            curve_signal = 1 if (yield_10y - yield_2y) < 0 else 0

            spy_hist = algorithm.History("SPY", 200, Resolution.Daily)["close"]
            ma50  = spy_hist.iloc[-50:].mean()
            ma200 = spy_hist.iloc[-200:].mean()
            mom_signal = 1 if ma50 < ma200 else 0

            credit_signal = 1 if algorithm.Securities["HYG"].Price / algorithm.Securities["TLT"].Price < 0.95 else 0

            raw = vol_signal + curve_signal + mom_signal + credit_signal
            return min(3, raw)  # 0=Green, 1=Yellow, 2=Orange, 3=Red
        except:
            return 0
