class LeveragedETFSwitcher:
    @staticmethod
    def symbol(algorithm, base, leveraged, inception_date):
        if algorithm.Time >= inception_date and leveraged in algorithm.Securities and algorithm.Securities[leveraged].HasData:
            return leveraged
        return base

    @staticmethod
    def equity(algorithm):   return LeveragedETFSwitcher.symbol(algorithm, "SPY",  "TQQQ", datetime(2010,2,11))
    @staticmethod
    def bond(algorithm):     return LeveragedETFSwitcher.symbol(algorithm, "TLT",  "TMF",  datetime(2009,4,16))
    @staticmethod
    def gold(algorithm):     return LeveragedETFSwitcher.symbol(algorithm, "GLD",  "UGL",  datetime(2008,12,1))
    @staticmethod
    def silver(algorithm):   return LeveragedETFSwitcher.symbol(algorithm, "SLV",  "AGQ",  datetime(2009,5,29))
    @staticmethod
    def volatility(algorithm): return LeveragedETFSwitcher.symbol(algorithm, "VXX", "UVXY", datetime(2011,10,4))
