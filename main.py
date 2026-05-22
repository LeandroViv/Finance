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

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN"]

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/prices")
async def get_prices():
    results = {}
    for symbol in SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                results[symbol] = round(float(price), 2)
            else:
                results[symbol] = None
        except:
            results[symbol] = None
    return results

@app.get("/api/historical")
async def get_historical(symbol: str, days: int = 60):
    try:
        ticker = yf.Ticker(symbol)
        end = datetime.now()
        start = end - timedelta(days=days)
        hist = ticker.history(start=start, end=end)
        if not hist.empty:
            prices = [round(float(p), 2) for p in hist['Close'].tolist()]
            return {"symbol": symbol, "prices": prices, "count": len(prices)}
    except Exception as e:
        return {"symbol": symbol, "prices": [], "error": str(e)}
    return {"symbol": symbol, "prices": []}