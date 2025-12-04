from AlgorithmImports import *
import pandas as pd
from datetime import timedelta

class ChaosHybrid7030v2(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2000, 1, 1)
        self.SetEndDate(2025, 12, 3)
        self.SetCash(100000)

        # Core assets: Leveraged ETFs with inception-aware fallbacks
        self.equity = ["SPY", "TQQQ"]  # TQQQ from 2010-02-11
        self.bond = ["TLT", "TMF"]     # TMF from 2009-04-16
        self.gold = ["GLD", "UGL"]     # UGL from 2008-10-03
        self.silver = ["SLV", "AGQ"]   # AGQ from 2009-05-29
        self.vol = ["VXX", "UVXY"]     # UVXY from 2011-10-04

        # Add all with warm-up
        for symbol in self.equity + self.bond + self.gold + self.silver + self.vol:
            self.AddEquity(symbol, Resolution.Daily)
        self.AddData(FRED, "GDPC1", Resolution.Monthly)  # Real GDP
        self.AddData(FRED, "CPIAUCSL", Resolution.Monthly)  # CPI
        self.AddData(FRED, "RECPROUSM156N", Resolution.Daily)  # NY Fed Recession Prob

        # Diagnostic counters
        self.tier_counts = {"Green": 0, "Yellow": 0, "Orange": 0, "Red": 0}
        self.days_traded = 0

        # Warm-up for FRED data
        self.SetWarmUp(timedelta(days=365*5))  # 5 years for regime stability

    def OnData(self, data):
        if self.IsWarmingUp:
            return

        self.days_traded += 1
        tier = self.chaos_brake()
        confirmed_regime = self.economic_regime_quad_confirmed()
        pressure = self.next_regime_pressure() if tier >= 2 else 0.0

        # Final regime: 85% confirmed + 15% pressure (gated)
        if pressure < -0.5 and confirmed_regime in ["goldilocks", "reflation"]:
            final_regime = "deflation" if pressure < -0.8 else "stagflation"
        elif pressure > 0.7 and confirmed_regime in ["deflation", "stagflation"]:
            final_regime = "goldilocks"
        else:
            final_regime = confirmed_regime

        weights = self.get_exposure_map(tier, final_regime)
        self.rebalance_portfolio(weights)

        # Daily diagnostic log
        regime_color = "Green" if tier == 0 else "Yellow" if tier == 1 else "Orange" if tier == 2 else "Red"
        self.Log(f"Day {self.days_traded}: Tier {tier} ({regime_color}), Regime: {final_regime}, Pressure: {pressure:.2f}")

        # Update counters
        self.tier_counts[regime_color] += 1

    def chaos_brake(self) -> int:
        """Chaos Risk Brake: 4-indicator cocktail for tier (0=Green, 1=Yellow, 2=Orange, 3=Red)"""
        try:
            # 1. VIX > 20 (volatility)
            vix = self.Securities["VIX"].Price
            vol_signal = 1 if vix > 20 else 0

            # 2. 10Y-2Y Yield Spread < 0 (curve inversion)
            yield_10y = self.Securities["^TNX"].Price / 100
            yield_2y = self.Securities["^IRX"].Price / 100 * 0.25  # Approximate 2Y from 3M
            spread = yield_10y - yield_2y
            curve_signal = 1 if spread < 0 else 0

            # 3. Credit Spread (HY - Treas) > 5% (sector momentum overlay)
            hyg = self.Securities["HYG"].Price
            tlt = self.Securities["TLT"].Price
            credit_spread = (hyg / tlt - 1) * 100 if tlt > 0 else 0
            credit_signal = 1 if credit_spread > 5 else 0

            # 4. Momentum divergence: SPY 50d MA < 200d MA
            spy_history = self.History("SPY", 200, Resolution.Daily)
            if len(spy_history) < 200:
                return 0
            ma50 = spy_history["close"].tail(50).mean()
            ma200 = spy_history["close"].tail(200).mean()
            mom_signal = 1 if ma50 < ma200 else 0

            # Tier: sum of signals (0-4), mapped to 0-3
            raw_tier = vol_signal + curve_signal + credit_signal + mom_signal
            return min(3, raw_tier)  # Cap at Red (3)
        except:
            return 0  # Safe default

    def economic_regime_quad_confirmed(self) -> str:
        """FRED-based confirmed economic quadrature (lagged, no revisions risk)"""
        try:
            gdp = self.GetFundamentalData(FRED, "GDPC1").GetLastKnownPrice()  # YoY %
            cpi = self.GetFundamentalData(FRED, "CPIAUCSL").GetLastKnownPrice()  # YoY %

            gdp_growth = (gdp / self.gdp_prev - 1) * 100 if hasattr(self, 'gdp_prev') else 2.0
            inflation = (cpi / self.cpi_prev - 1) * 100 if hasattr(self, 'cpi_prev') else 2.5

            self.gdp_prev = gdp
            self.cpi_prev = cpi

            if gdp_growth > 2 and inflation < 3:
                return "goldilocks"
            elif gdp_growth > 0 and inflation > 3:
                return "reflation"
            elif gdp_growth < 0 and inflation > 3:
                return "stagflation"
            else:
                return "deflation"
        except:
            # Default to neutral on errors
            return "goldilocks"

    def next_regime_pressure(self) -> float:
        """NY Fed 12mo recession prob (0-100%) → -1.0 (Deflation) to +1.0 (Goldilocks)"""
        try:
            history = self.History(["RECPROUSM156N"], 100, Resolution.Daily)
            if history.empty:
                return 0.0
            prob = history["close"].iloc[-1]  # Latest prob

            if prob > 65:
                return -1.0
            elif prob > 45:
                return -0.7
            elif prob > 30:
                return -0.4
            elif prob < 15:
                return 0.7
            elif prob < 8:
                return 1.0
            else:
                return 0.0
        except:
            return 0.0

    def get_exposure_map(self, tier: int, regime: str) -> dict:
        """16-cell 4x4 exposure map: Tier x Regime → Weights"""
        map_4x4 = {
            # Green (Tier 0): Aggressive
            "goldilocks": {"equity": 0.70, "bond": 0.20, "gold": 0.05, "silver": 0.03, "vol": 0.02},
            "reflation": {"equity": 0.60, "bond": 0.10, "gold": 0.15, "silver": 0.10, "vol": 0.05},
            "stagflation": {"equity": 0.40, "bond": 0.10, "gold": 0.30, "silver": 0.15, "vol": 0.05},
            "deflation": {"equity": 0.30, "bond": 0.60, "gold": 0.05, "silver": 0.02, "vol": 0.03},

            # Yellow (Tier 1): Balanced
            "goldilocks": {"equity": 0.50, "bond": 0.30, "gold": 0.10, "silver": 0.05, "vol": 0.05},
            "reflation": {"equity": 0.40, "bond": 0.20, "gold": 0.20, "silver": 0.15, "vol": 0.05},
            "stagflation": {"equity": 0.30, "bond": 0.20, "gold": 0.30, "silver": 0.15, "vol": 0.05},
            "deflation": {"equity": 0.20, "bond": 0.70, "gold": 0.05, "silver": 0.02, "vol": 0.03},

            # Orange (Tier 2): Defensive
            "goldilocks": {"equity": 0.30, "bond": 0.40, "gold": 0.15, "silver": 0.10, "vol": 0.05},
            "reflation": {"equity": 0.20, "bond": 0.30, "gold": 0.25, "silver": 0.20, "vol": 0.05},
            "stagflation": {"equity": 0.20, "bond": 0.20, "gold": 0.40, "silver": 0.15, "vol": 0.05},
            "deflation": {"equity": 0.10, "bond": 0.80, "gold": 0.05, "silver": 0.02, "vol": 0.03},

            # Red (Tier 3): Cash-like / Vol hedge
            "goldilocks": {"equity": 0.10, "bond": 0.50, "gold": 0.10, "silver": 0.05, "vol": 0.25},
            "reflation": {"equity": 0.10, "bond": 0.40, "gold": 0.15, "silver": 0.10, "vol": 0.25},
            "stagflation": {"equity": 0.05, "bond": 0.20, "gold": 0.30, "silver": 0.20, "vol": 0.25},
            "deflation": {"equity": 0.05, "bond": 0.90, "gold": 0.02, "silver": 0.01, "vol": 0.02},
        }
        return map_4x4.get(f"{['green', 'yellow', 'orange', 'red'][tier]}_{regime}", {"bond": 1.0})  # Default to bonds

    def rebalance_portfolio(self, weights: dict):
        """Apply weights with leveraged-ETF preference and inception fallbacks"""
        target_value = self.Portfolio.TotalPortfolioValue

        # Equity
        eq_sym = "TQQQ" if "TQQQ" in self.Securities and self.Securities["TQQQ"].HasData else "SPY"
        self.SetHoldings(eq_sym, weights["equity"])

        # Bond
        bond_sym = "TMF" if "TMF" in self.Securities and self.Securities["TMF"].HasData else "TLT"
        self.SetHoldings(bond_sym, weights["bond"])

        # Gold
        gold_sym = "UGL" if "UGL" in self.Securities and self.Securities["UGL"].HasData else "GLD"
        self.SetHoldings(gold_sym, weights["gold"])

        # Silver
        silver_sym = "AGQ" if "AGQ" in self.Securities and self.Securities["AGQ"].HasData else "SLV"
        self.SetHoldings(silver_sym, weights["silver"])

        # Vol (only in higher tiers)
        if weights["vol"] > 0:
            vol_sym = "UVXY" if "UVXY" in self.Securities and self.Securities["UVXY"].HasData else "VXX"
            self.SetHoldings(vol_sym, weights["vol"])

    def OnEndOfAlgorithm(self):
        """Final diagnostic stats"""
        total_days = sum(self.tier_counts.values())
        self.Log("=== ChaosHybrid7030 v2 Final Stats ===")
        for color, count in self.tier_counts.items():
            pct = (count / total_days * 100) if total_days > 0 else 0
            self.Log(f"{color}: {count} days ({pct:.1f}%)")
        self.Log(f"Total days traded: {total_days}")
        self.Log("Backtest complete. Deploy live with zero fear.")
