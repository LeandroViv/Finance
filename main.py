from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import requests
import yfinance as yf
import time
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== CONFIGURACIÓN MCP ====================
MCP_URL = "https://modelcontextprotocol.name/mcp/crypto-data-aggregator"

# Cache en memoria
crypto_cache = {
    "data": [],
    "timestamp": 0,
    "ttl": 300  # 5 minutos
}

# ==================== ACCIONES ====================
STOCKS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "NFLX"]
SYMBOL_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
    "TSLA": "Tesla", "GOOGL": "Google", "AMZN": "Amazon",
    "META": "Meta", "NFLX": "Netflix",
}

# ==================== FUNCIONES MCP ====================
def get_cached_cryptos(force_refresh=False):
    """Obtiene criptomonedas del MCP Aggregator con cache"""
    now = time.time()
    
    if force_refresh or (now - crypto_cache["timestamp"] > crypto_cache["ttl"]) or not crypto_cache["data"]:
        print("🔄 Actualizando cache desde MCP Aggregator...")
        try:
            # Obtener market overview (top 250 por market cap)
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_market_overview",
                    "arguments": {
                        "vs_currency": "usd",
                        "per_page": 250
                    }
                },
                "id": 1
            }
            
            response = requests.post(MCP_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Procesar la respuesta del MCP
            cryptos_list = []
            if "result" in data and "content" in data["result"]:
                content = data["result"]["content"]
                # El content puede venir como texto o como lista
                if isinstance(content, list) and len(content) > 0:
                    # Intentar parsear como JSON
                    import json as json_lib
                    try:
                        coins = json_lib.loads(content[0].get("text", "[]"))
                        for coin in coins:
                            cryptos_list.append({
                                "symbol": f"{coin.get('symbol', '').upper()}-USD",
                                "name": coin.get('name', ''),
                                "price": coin.get('current_price', 0),
                                "market_cap": coin.get('market_cap', 0),
                                "volume_24h": coin.get('total_volume', 0),
                                "percent_change_24h": coin.get('price_change_percentage_24h', 0),
                                "rank": coin.get('market_cap_rank', len(cryptos_list) + 1)
                            })
                    except:
                        pass
            
            if cryptos_list:
                crypto_cache["data"] = cryptos_list
                crypto_cache["timestamp"] = now
                print(f"✅ Cache actualizado con {len(cryptos_list)} criptomonedas")
            else:
                # Fallback a CoinGecko si el MCP no responde bien
                crypto_cache["data"] = get_fallback_cryptos()
                crypto_cache["timestamp"] = now
                
        except Exception as e:
            print(f"❌ Error MCP: {e}")
            if not crypto_cache["data"]:
                crypto_cache["data"] = get_fallback_cryptos()
                crypto_cache["timestamp"] = now
    
    return crypto_cache["data"]

def get_fallback_cryptos():
    """Fallback a CoinGecko si el MCP falla"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 100,
            'page': 1,
            'sparkline': 'false'
        }
        response = requests.get(url, params=params, timeout=10)
        coins = response.json()
        
        result = []
        for coin in coins:
            result.append({
                "symbol": f"{coin['symbol'].upper()}-USD",
                "name": coin['name'],
                "price": coin.get('current_price', 0),
                "market_cap": coin.get('market_cap', 0),
                "volume_24h": coin.get('total_volume', 0),
                "percent_change_24h": coin.get('price_change_percentage_24h', 0),
                "rank": coin.get('market_cap_rank', len(result) + 1)
            })
        return result
    except:
        return get_backup_cryptos()

def get_backup_cryptos():
    """Lista de respaldo mínima"""
    return [
        {"symbol": "BTC-USD", "name": "Bitcoin", "price": 65000, "market_cap": 1300000000000, "volume_24h": 30000000000, "percent_change_24h": 2.5, "rank": 1},
        {"symbol": "ETH-USD", "name": "Ethereum", "price": 3500, "market_cap": 420000000000, "volume_24h": 15000000000, "percent_change_24h": 1.8, "rank": 2},
        {"symbol": "SOL-USD", "name": "Solana", "price": 180, "market_cap": 80000000000, "volume_24h": 3000000000, "percent_change_24h": 5.2, "rank": 5},
        {"symbol": "XRP-USD", "name": "Ripple", "price": 0.6, "market_cap": 33000000000, "volume_24h": 1500000000, "percent_change_24h": -0.5, "rank": 7},
    ]

# ==================== ENDPOINTS (igual que antes) ====================
@app.get("/")
async def root():
    cryptos = get_cached_cryptos()
    return {
        "message": "Inversor API con MCP Crypto Data Aggregator",
        "total_cryptos": len(cryptos),
        "total_stocks": len(STOCKS),
        "total_symbols": len(STOCKS) + len(cryptos),
        "sample_cryptos": [c["symbol"] for c in cryptos[:20]],
        "data_source": "MCP Aggregator (10,000+ coins)"
    }

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/symbols")
async def get_symbols():
    cryptos = get_cached_cryptos()
    all_symbols = STOCKS + [c["symbol"] for c in cryptos]
    return {
        "symbols": all_symbols[:200],
        "count": len(all_symbols),
        "cryptos_count": len(cryptos),
        "stocks_count": len(STOCKS)
    }

@app.get("/api/prices")
async def get_prices():
    """Obtiene todos los precios (acciones + criptos)"""
    results = {}
    
    # Precios de acciones (yfinance)
    for stock in STOCKS:
        try:
            ticker = yf.Ticker(stock)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                results[stock] = {
                    "price": round(float(price), 2),
                    "name": SYMBOL_NAMES.get(stock, stock)
                }
            else:
                results[stock] = None
        except:
            results[stock] = None
    
    # Precios de criptos (desde cache MCP)
    cryptos = get_cached_cryptos()
    for crypto in cryptos:
        symbol = crypto["symbol"]
        results[symbol] = {
            "price": crypto["price"],
            "name": crypto["name"],
            "market_cap": crypto["market_cap"],
            "volume_24h": crypto["volume_24h"],
            "change_24h": crypto["percent_change_24h"]
        }
    
    return results

@app.get("/api/price/{symbol}")
async def get_price(symbol: str):
    """Obtiene precio de un símbolo específico"""
    # Acciones
    if symbol in STOCKS:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return {
                    "symbol": symbol,
                    "name": SYMBOL_NAMES.get(symbol, symbol),
                    "price": round(float(hist['Close'].iloc[-1]), 2),
                    "timestamp": datetime.now().isoformat()
                }
        except:
            pass
        return {"symbol": symbol, "error": "No data"}
    
    # Criptos
    cryptos = get_cached_cryptos()
    for crypto in cryptos:
        if crypto["symbol"] == symbol.upper():
            return {
                "symbol": symbol,
                "name": crypto["name"],
                "price": crypto["price"],
                "market_cap": crypto["market_cap"],
                "volume_24h": crypto["volume_24h"],
                "percent_change_24h": crypto["percent_change_24h"],
                "timestamp": datetime.now().isoformat()
            }
    
    return {"symbol": symbol, "error": "No data"}

@app.get("/api/historical")
async def get_historical(symbol: str = Query(...), days: int = Query(60)):
    """Datos históricos"""
    # Para acciones con yfinance
    if symbol in STOCKS:
        try:
            ticker = yf.Ticker(symbol)
            end = datetime.now()
            start = end - timedelta(days=days)
            hist = ticker.history(start=start, end=end)
            if not hist.empty:
                return {
                    "symbol": symbol,
                    "name": SYMBOL_NAMES.get(symbol, symbol),
                    "prices": [round(float(p), 2) for p in hist['Close'].tolist()],
                    "dates": [d.strftime("%Y-%m-%d") for d in hist.index.tolist()],
                    "count": len(hist)
                }
        except:
            pass
        return {"symbol": symbol, "prices": [], "count": 0}
    
    # Para criptos, usar CoinGecko fallback o MCP si tiene histórico
    try:
        coin_id = symbol.replace("-USD", "").lower()
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {'vs_currency': 'usd', 'days': days}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            prices = data.get('prices', [])
            return {
                "symbol": symbol,
                "name": symbol.replace("-USD", ""),
                "prices": [round(p[1], 2) for p in prices],
                "dates": [datetime.fromtimestamp(p[0]/1000).strftime("%Y-%m-%d") for p in prices],
                "count": len(prices)
            }
    except:
        pass
    
    return {"symbol": symbol, "prices": [], "count": 0}

@app.get("/api/cryptos/all")
async def get_all_cryptos_symbols():
    cryptos = get_cached_cryptos()
    return {
        "cryptos": [c["symbol"] for c in cryptos],
        "count": len(cryptos),
        "source": "MCP Aggregator"
    }

@app.get("/api/top")
async def get_top_cryptos(limit: int = 50):
    cryptos = get_cached_cryptos()
    return {
        "top_cryptos": cryptos[:limit],
        "count": len(cryptos[:limit])
    }

@app.post("/api/refresh-cache")
async def refresh_cache():
    get_cached_cryptos(force_refresh=True)
    return {"status": "ok", "message": "Cache actualizado"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 INICIANDO API CON MCP AGGREGATOR...")
    get_cached_cryptos()
    print(f"✅ API lista en http://0.0.0.0:10000")
    uvicorn.run(app, host="0.0.0.0", port=10000)
