from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import requests
import yfinance as yf
import time
import json
from collections import OrderedDict

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== CONFIGURACIÓN ====================
# IMPORTANTE: Cambiá esta URL por la de TU aggregator después de deployarlo
# Si deployás el aggregator en Render, va a ser algo como:
# AGGREGATOR_URL = "https://crypto-aggregator.onrender.com"
# Por ahora usamos la demo pública, pero te recomiendo deployar el tuyo propio
AGGREGATOR_URL = "https://crypto-data-aggregator.onrender.com"  # Demo pública (cambiala después)

# Cache en memoria para no llamar al aggregator todo el tiempo
crypto_cache = {
    "data": [],
    "timestamp": 0,
    "ttl": 300  # 5 minutos de cache
}

# ==================== ACCIONES TOP ====================
STOCKS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "NFLX"]
SYMBOL_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
    "TSLA": "Tesla", "GOOGL": "Google", "AMZN": "Amazon",
    "META": "Meta", "NFLX": "Netflix",
}

# ==================== FUNCIONES DEL AGGREGATOR ====================
def get_cached_cryptos(force_refresh=False):
    """
    Obtiene criptomonedas del cache o del aggregator
    El aggregator devuelve ~10,000+ criptomonedas rankeadas por market cap
    """
    now = time.time()
    
    if force_refresh or (now - crypto_cache["timestamp"] > crypto_cache["ttl"]) or not crypto_cache["data"]:
        print("🔄 Actualizando cache desde el Crypto Data Aggregator...")
        try:
            # Endpoint del aggregator para obtener el ranking completo
            url = f"{AGGREGATOR_URL}/api/market/coins"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # El aggregator devuelve { "coins": [ ... ] }
            coins = data.get('coins', []) if isinstance(data, dict) else data
            
            # Transformar al formato que espera tu frontend
            cryptos_list = []
            for coin in coins[:500]:  # Limitamos a 500 para performance (podés aumentar)
                # Obtener precio según la estructura del aggregator
                current_price = coin.get('current_price', 0)
                if not current_price:
                    current_price = coin.get('price', 0) or coin.get('usd', 0)
                
                market_cap = coin.get('market_cap', 0)
                if not market_cap:
                    market_cap = coin.get('marketCap', 0)
                
                volume = coin.get('total_volume', 0)
                if not volume:
                    volume = coin.get('volume', 0)
                
                change = coin.get('price_change_percentage_24h', 0)
                if not change:
                    change = coin.get('change_24h', 0)
                
                cryptos_list.append({
                    "symbol": f"{coin['symbol'].upper()}-USD",
                    "name": coin['name'],
                    "price": round(float(current_price), 4) if current_price else 0,
                    "market_cap": market_cap,
                    "volume_24h": volume,
                    "percent_change_24h": change,
                    "rank": coin.get('market_cap_rank', len(cryptos_list) + 1)
                })
            
            crypto_cache["data"] = cryptos_list
            crypto_cache["timestamp"] = now
            print(f"✅ Cache actualizado con {len(cryptos_list)} criptomonedas")
            print(f"📝 Ejemplos: {[c['symbol'] for c in cryptos_list[:10]]}")
            
        except Exception as e:
            print(f"❌ Error obteniendo datos del aggregator: {e}")
            # Si falla el aggregator, usar datos de respaldo
            if not crypto_cache["data"]:
                crypto_cache["data"] = get_backup_cryptos()
                crypto_cache["timestamp"] = now
                print("⚠️ Usando datos de respaldo")
    
    return crypto_cache["data"]

def get_backup_cryptos():
    """Lista de respaldo por si falla el aggregator"""
    return [
        {"symbol": "BTC-USD", "name": "Bitcoin", "price": 65000, "market_cap": 1300000000000, "volume_24h": 30000000000, "percent_change_24h": 2.5, "rank": 1},
        {"symbol": "ETH-USD", "name": "Ethereum", "price": 3500, "market_cap": 420000000000, "volume_24h": 15000000000, "percent_change_24h": 1.8, "rank": 2},
        {"symbol": "BNB-USD", "name": "BNB", "price": 600, "market_cap": 90000000000, "volume_24h": 2000000000, "percent_change_24h": 0.5, "rank": 4},
        {"symbol": "SOL-USD", "name": "Solana", "price": 180, "market_cap": 80000000000, "volume_24h": 3000000000, "percent_change_24h": 5.2, "rank": 5},
        {"symbol": "XRP-USD", "name": "Ripple", "price": 0.6, "market_cap": 33000000000, "volume_24h": 1500000000, "percent_change_24h": -0.5, "rank": 7},
        {"symbol": "ADA-USD", "name": "Cardano", "price": 0.45, "market_cap": 16000000000, "volume_24h": 400000000, "percent_change_24h": 3.2, "rank": 10},
        {"symbol": "DOGE-USD", "name": "Dogecoin", "price": 0.15, "market_cap": 21000000000, "volume_24h": 800000000, "percent_change_24h": -1.2, "rank": 9},
        {"symbol": "AVAX-USD", "name": "Avalanche", "price": 35, "market_cap": 13000000000, "volume_24h": 350000000, "percent_change_24h": 4.1, "rank": 12},
    ]

# ==================== ENDPOINTS ====================
@app.get("/")
async def root():
    cryptos = get_cached_cryptos()
    return {
        "message": "Inversor API con Crypto Data Aggregator (0 créditos, 10,000+ criptos)",
        "total_cryptos": len(cryptos),
        "total_stocks": len(STOCKS),
        "total_symbols": len(STOCKS) + len(cryptos),
        "sample_cryptos": [c["symbol"] for c in cryptos[:20]],
        "data_source": "Crypto Data Aggregator (self-hosted, open source)",
        "cache_ttl_seconds": crypto_cache["ttl"]
    }

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/symbols")
async def get_symbols():
    cryptos = get_cached_cryptos()
    all_symbols = STOCKS + [c["symbol"] for c in cryptos]
    return {
        "symbols": all_symbols[:200],  # Limitamos a 200 para no saturar
        "count": len(all_symbols),
        "cryptos_count": len(cryptos),
        "stocks_count": len(STOCKS)
    }

@app.get("/api/prices")
async def get_prices():
    """Obtiene precios actualizados (acciones de yfinance, criptos del aggregator)"""
    results = {}
    
    # Precios de acciones con yfinance
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
        except Exception as e:
            print(f"Error con {stock}: {e}")
            results[stock] = None
    
    # Precios de criptos desde el cache del aggregator
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
    # Si es acción
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
    
    # Si es cripto, buscar en el cache
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
async def get_historical(
    symbol: str = Query(...),
    days: int = Query(60)
):
    """Obtiene datos históricos"""
    # Para acciones, usar yfinance
    if symbol in STOCKS:
        try:
            ticker = yf.Ticker(symbol)
            end = datetime.now()
            start = end - timedelta(days=days)
            hist = ticker.history(start=start, end=end)
            
            if not hist.empty:
                prices = [round(float(p), 2) for p in hist['Close'].tolist()]
                dates = [d.strftime("%Y-%m-%d") for d in hist.index.tolist()]
                return {
                    "symbol": symbol,
                    "name": SYMBOL_NAMES.get(symbol, symbol),
                    "prices": prices,
                    "dates": dates,
                    "count": len(prices)
                }
        except:
            pass
        return {"symbol": symbol, "prices": [], "count": 0}
    
    # Para criptos, intentar con el aggregator
    try:
        coin_id = symbol.replace("-USD", "").lower()
        url = f"{AGGREGATOR_URL}/api/market/history/{coin_id}?days={days}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            prices_data = data.get('prices', [])
            if prices_data:
                return {
                    "symbol": symbol,
                    "name": symbol.replace("-USD", ""),
                    "prices": [round(p[1], 2) for p in prices_data[-days:]],
                    "dates": [datetime.fromtimestamp(p[0]/1000).strftime("%Y-%m-%d") for p in prices_data[-days:]],
                    "count": len(prices_data)
                }
    except Exception as e:
        print(f"Error histórico {symbol}: {e}")
    
    return {"symbol": symbol, "prices": [], "count": 0}

@app.get("/api/cryptos/all")
async def get_all_cryptos_symbols():
    """Devuelve la lista completa de símbolos de criptomonedas"""
    cryptos = get_cached_cryptos()
    return {
        "cryptos": [c["symbol"] for c in cryptos],
        "count": len(cryptos),
        "source": "Crypto Data Aggregator"
    }

@app.get("/api/top")
async def get_top_cryptos(limit: int = 50):
    """Devuelve las TOP N criptomonedas con datos completos"""
    cryptos = get_cached_cryptos()
    return {
        "top_cryptos": cryptos[:limit],
        "count": len(cryptos[:limit]),
        "total_available": len(cryptos)
    }

@app.post("/api/refresh-cache")
async def refresh_cache():
    """Endpoint para forzar actualización del cache"""
    get_cached_cryptos(force_refresh=True)
    return {"status": "ok", "message": "Cache actualizado manualmente"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 INICIANDO API CON CRYPTO DATA AGGREGATOR...")
    print("📡 Obteniendo primeras criptomonedas...")
    get_cached_cryptos()  # Precargar cache
    print(f"✅ API lista en http://0.0.0.0:10000")
    print(f"🎯 Total criptos en cache: {len(crypto_cache['data'])}")
    uvicorn.run(app, host="0.0.0.0", port=10000)
