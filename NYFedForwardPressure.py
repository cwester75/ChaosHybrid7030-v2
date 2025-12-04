class NYFedForwardPressure:
    """Market-implied regime pressure – only activates when Chaos Tier ≥ 2"""
    @staticmethod
    def get_pressure(algorithm, tier: int) -> float:
        if tier < 2:
            return 0.0
        try:
            prob = algorithm.History("RECPROUSM156N", 10, Resolution.Daily)["close"].iloc[-1]
            if prob > 65:  return -1.0
            if prob > 45:  return -0.7
            if prob > 30:  return -0.4
            if prob < 15:  return +0.7
            if prob < 8:   return +1.0
            return 0.0
        except:
            return 0.0
