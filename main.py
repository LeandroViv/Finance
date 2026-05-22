from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== SÍMBOLOS ====================
SYMBOLS = [
    # Acciones
    "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN",
    # Criptomonedas
    "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "XRP-USD",
    "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD"
]

# Nombre legible para cada símbolo
SYMBOL_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
    "TSLA": "Tesla", "GOOGL": "Google", "AMZN": "Amazon",
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana",
    "DOGE-USD": "Dogecoin", "XRP-USD": "Ripple", "ADA-USD": "Cardano",
    "AVAX-USD": "Avalanche", "DOT-USD": "Polkadot", "LINK-USD": "Chainlink",
    "MATIC-USD": "Polygon"
}

@app.get("/")
async def root():
    return {
        "message": "Inversor API con criptomonedas",
        "symbols": SYMBOLS,
        "count": len(SYMBOLS)
    }

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/symbols")
async def get_symbols():
    """Devuelve la lista de símbolos disponibles"""
    return {"symbols": SYMBOLS, "names": SYMBOL_NAMES, "count": len(SYMBOLS)}

@app.get("/api/price/{symbol}")
async def get_price(symbol: str):
    """Obtiene el precio de un símbolo específico"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
            return {
                "symbol": symbol,
                "name": SYMBOL_NAMES.get(symbol, symbol),
                "price": round(float(price), 2),
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}
    return {"symbol": symbol, "error": "No data"}

@app.get("/api/prices")
async def get_all_prices():
    """Obtiene todos los precios actuales (acciones + criptos)"""
    results = {}
    for symbol in SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                results[symbol] = {
                    "price": round(float(price), 2),
                    "name": SYMBOL_NAMES.get(symbol, symbol)
                }
            else:
                results[symbol] = None
        except Exception as e:
            print(f"Error con {symbol}: {e}")
            results[symbol] = None
    return results

@app.get("/api/historical")
async def get_historical(
    symbol: str = Query(..., description="Símbolo del activo"),
    days: int = Query(60, description="Cantidad de días")
):
    """Obtiene precios históricos"""
    try:
        ticker = yf.Ticker(symbol)
        end = datetime.now()
        start = end - timedelta(days=days)
        hist = ticker.history(start=start, end=end)
        
        if not hist.empty:
            prices = [round(float(p), 2) for p in hist['Close'].tolist()]
            return {
                "symbol": symbol,
                "name": SYMBOL_NAMES.get(symbol, symbol),
                "prices": prices,
                "count": len(prices)
            }
        else:
            return {"symbol": symbol, "prices": [], "count": 0}
    except Exception as e:
        return {"symbol": symbol, "prices": [], "error": str(e)}
