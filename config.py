"""
Trading Platform Configuration - Comprehensive Stock & Crypto Lists
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data_cache"
DB_PATH = BASE_DIR / "trading.db"
DATA_DIR.mkdir(exist_ok=True)

# ===== STOCKS BY INDUSTRY =====

TECH_STOCKS = [
    # Mega Cap Tech
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    # Semiconductors
    "AMD", "INTC", "QCOM", "AVGO", "TXN", "MU", "MRVL", "LRCX", "KLAC", "AMAT",
    "ASML", "TSM", "NXPI", "ON", "ADI", "MCHP", "SWKS", "QRVO",
    # Software
    "CRM", "ORCL", "ADBE", "NOW", "INTU", "SNOW", "PLTR", "PANW", "CRWD", "ZS",
    "DDOG", "NET", "MDB", "TEAM", "OKTA", "HUBS", "VEEV", "WDAY", "FTNT",
    # Cloud & Internet
    "SHOP", "PYPL", "SPOT", "UBER", "LYFT", "ABNB", "DASH", "RBLX", "U",
    "SNAP", "PINS", "TWLO", "ZM", "DOCU", "DBX", "BOX", "PATH",
    # Hardware
    "DELL", "HPQ", "HPE", "LOGI", "WDC", "STX",
]

HEALTHCARE_STOCKS = [
    # Pharma Giants
    "JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY", "AMGN", "GILD", "REGN", "VRTX",
    "BIIB", "MRNA", "BNTX", "AZN", "NVO", "GSK", "SNY", "NVS",
    # Medical Devices
    "MDT", "ABT", "SYK", "ISRG", "BSX", "EW", "ZBH", "DXCM", "ALGN",
    "IDXX", "BDX", "BAX", "TMO", "DHR", "A", "ILMN", "PODD",
    # Health Insurance
    "UNH", "CVS", "CI", "HUM", "CNC", "HCA",
    # Biotech
    "ALNY", "SRPT", "BMRN", "IONS", "NBIX", "EXEL", "RXRX",
]

FINANCE_STOCKS = [
    # Big Banks
    "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "SCHW",
    "BK", "STT", "NTRS", "CFG", "KEY", "RF", "HBAN", "FITB", "MTB",
    # Investment Management
    "BLK", "BX", "KKR", "APO", "ARES", "TROW", "IVZ", "BEN",
    # Insurance
    "BRK-B", "AIG", "MET", "PRU", "ALL", "TRV", "CB", "PGR", "AFL", "HIG",
    # Fintech & Payments
    "V", "MA", "AXP", "COF", "SYF", "ALLY", "SOFI", "AFRM", "UPST", "NU",
    # Exchanges
    "CME", "ICE", "NDAQ", "CBOE", "COIN",
]

ENERGY_STOCKS = [
    # Oil Majors
    "XOM", "CVX", "COP", "EOG", "OXY", "MPC", "VLO", "PSX",
    "DVN", "FANG", "APA", "HAL", "SLB", "BKR", "OVV", "TPL",
    # Natural Gas
    "LNG", "EQT", "AR", "RRC", "CHRD",
    # Renewables
    "NEE", "ENPH", "SEDG", "FSLR", "RUN", "PLUG", "BE",
    # Utilities
    "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ES", "ED",
]

CONSUMER_STOCKS = [
    # Retail
    "WMT", "COST", "TGT", "HD", "LOW", "DG", "DLTR", "ROST", "TJX", "BBY",
    "ULTA", "LULU", "ANF", "AEO", "BURL",
    # E-commerce
    "EBAY", "ETSY", "W", "CHWY",
    # Consumer Products
    "PG", "KO", "PEP", "MNST", "KDP", "KHC", "GIS", "CPB",
    "HSY", "MDLZ", "CL", "CLX", "CHD", "EL", "SJM",
    # Restaurants
    "MCD", "SBUX", "CMG", "YUM", "DRI", "SHAK", "WING",
    # Apparel
    "NKE", "LEVI", "VFC", "PVH", "RL", "TPR",
]

INDUSTRIAL_STOCKS = [
    # Aerospace & Defense
    "BA", "LMT", "RTX", "NOC", "GD", "LHX", "HII", "TDG",
    # Manufacturing
    "CAT", "DE", "HON", "MMM", "EMR", "ETN", "ROK", "PH", "ITW", "IR",
    "DOV", "XYL",
    # Transport
    "UPS", "FDX", "UNP", "CSX", "NSC", "DAL", "UAL", "AAL", "LUV",
    "XPO", "ODFL",
    # Construction
    "SHW", "VMC", "MLM", "JCI", "CARR", "TT", "OTIS", "NVR", "LEN", "DHI", "PHM",
]

COMMUNICATION_STOCKS = [
    # Telecom
    "T", "VZ", "TMUS",
    # Media
    "DIS", "NFLX", "CMCSA", "WBD", "FOX", "LYV", "ROKU",
    # Gaming
    "EA", "TTWO", "DKNG", "PENN", "MGM", "CZR", "WYNN", "LVS", "GLBE",
]

MATERIALS_STOCKS = [
    # Mining
    "NEM", "FCX", "AA", "CLF", "NUE", "STLD", "RS",
    # Chemicals
    "LIN", "APD", "ECL", "DD", "DOW", "PPG", "ALB", "EMN",
    "FMC", "MOS", "CF", "NTR",
]

REAL_ESTATE_STOCKS = [
    "AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB",
    "EQR", "VTR", "ARE", "BXP", "KIM", "REG", "HST", "MAA", "UDR", "ESS",
]

# ===== DANISH STOCKS (Copenhagen Stock Exchange) =====
DANISH_STOCKS = [
    # Large Cap
    "NOVO-B.CO", "MAERSK-B.CO", "DSV.CO", "VWS.CO", "ORSTED.CO",
    "CARL-B.CO", "PNDORA.CO", "COLO-B.CO", "GMAB.CO", "DEMANT.CO",
    # Finance
    "DANSKE.CO", "TRYG.CO", "JYSK.CO",
    # Industrial
    "ROCK-B.CO", "FLS.CO", "ISS.CO", "GN.CO", "AMBU-B.CO",
    # Other
    "RBREW.CO", "NNIT.CO", "NETC.CO", "CHEMM.CO",
    "RILBA.CO", "MATAS.CO", "ALK-B.CO", "BAVA.CO",
]

# All stocks combined
ALL_STOCKS = (
    TECH_STOCKS + HEALTHCARE_STOCKS + FINANCE_STOCKS + ENERGY_STOCKS +
    CONSUMER_STOCKS + INDUSTRIAL_STOCKS + COMMUNICATION_STOCKS +
    MATERIALS_STOCKS + REAL_ESTATE_STOCKS + DANISH_STOCKS
)

# Industry mapping
INDUSTRIES = {
    "Tech": TECH_STOCKS,
    "Healthcare": HEALTHCARE_STOCKS,
    "Finance": FINANCE_STOCKS,
    "Energy": ENERGY_STOCKS,
    "Consumer": CONSUMER_STOCKS,
    "Industrial": INDUSTRIAL_STOCKS,
    "Communication": COMMUNICATION_STOCKS,
    "Materials": MATERIALS_STOCKS,
    "Real Estate": REAL_ESTATE_STOCKS,
    "Danish": DANISH_STOCKS,
}

# ===== CRYPTO (Yahoo Finance format) =====
CRYPTO_SYMBOLS = [
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD", "SOL-USD",
    "DOGE-USD", "DOT-USD", "SHIB-USD", "TRX-USD", "AVAX-USD",
    "LINK-USD", "ATOM-USD", "LTC-USD", "ETC-USD", "XLM-USD",
    "BCH-USD", "FIL-USD", "NEAR-USD", "ARB-USD", "OP-USD",
    "AAVE-USD", "MKR-USD", "LDO-USD", "CRV-USD", "HBAR-USD",
    "ALGO-USD", "SAND-USD", "MANA-USD", "AXS-USD", "GALA-USD", "ENJ-USD",
    "INJ-USD", "SEI-USD", "RENDER-USD", "ICP-USD", "WIF-USD", "VET-USD",
]

# ===== FOREX =====
FOREX_PAIRS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X",
    "NZDUSD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "CADJPY=X",
]

# Legacy support
POPULAR_STOCKS = TECH_STOCKS[:15]
POPULAR_CRYPTO = CRYPTO_SYMBOLS[:10]
POPULAR_FOREX = FOREX_PAIRS[:8]

# ===== NEWS SOURCES (RSS) =====
NEWS_RSS_FEEDS = {
    # General Market News
    "reuters": "https://www.reutersagency.com/feed/",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "wsj_markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "barrons": "https://www.barrons.com/feed",
    "bloomberg": "https://feeds.bloomberg.com/markets/news.rss",

    # Crypto News
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "cryptonews": "https://cryptonews.com/news/feed/",
    "decrypt": "https://decrypt.co/feed",

    # Analysis
    "seeking_alpha": "https://seekingalpha.com/market_currents.xml",
    "benzinga": "https://www.benzinga.com/feed",
    "motley_fool": "https://www.fool.com/feeds/index.aspx",
    "zacks": "https://www.zacks.com/feeds/rss.php",
    "investopedia": "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline",
}

# ===== API ENDPOINTS =====
API_ENDPOINTS = {
    "fear_greed_crypto": "https://api.alternative.me/fng/",
    "fear_greed_cnn": "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
    "finviz_screener": "https://finviz.com/screener.ashx",
    "tradingview": "https://scanner.tradingview.com/america/scan",
}

# ===== SETTINGS =====
DEFAULT_MODE = "paper"
DEFAULT_PAPER_BALANCE = 100000
REFRESH_INTERVAL = 30  # Auto-refresh interval in seconds
CACHE_EXPIRY = 300  # Cache data for 5 minutes

# Technical analysis
DEFAULT_RSI_PERIOD = 14
DEFAULT_SMA_PERIODS = [20, 50, 200]
DEFAULT_MACD_PARAMS = (12, 26, 9)
DEFAULT_BB_PARAMS = (20, 2)
