class EconomicQuadrature:
    """Confirmed, revision-proof FRED regime (no nowcasts, no surveys)"""
    @staticmethod
    def get_regime(algorithm) -> str:
        try:
            gdp = algorithm.History(FRED("GDPC1"), 730, Resolution.Daily)["close"].iloc[-1]
            cpi = algorithm.History(FRED("CPIAUCSL"), 730, Resolution.Daily)["close"].iloc[-1]
            gdp_yoy = (gdp / algorithm.gdp_prev - 1) * 100 if hasattr(algorithm, 'gdp_prev') else 2.0
            cpi_yoy = (cpi / algorithm.cpi_prev - 1) * 100 if hasattr(algorithm, 'cpi_prev') else 2.5
            algorithm.gdp_prev, algorithm.cpi_prev = gdp, cpi

            if gdp_yoy > 2 and cpi_yoy < 3:   return "goldilocks"
            if gdp_yoy > 0 and cpi_yoy > 3:   return "reflation"
            if gdp_yoy < 0 and cpi_yoy > 3:   return "stagflation"
            return "deflation"
        except:
            return "goldilocks"
