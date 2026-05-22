from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from datetime import datetime, timedelta
from yahooquery import Screener
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== OBTENER TODAS LAS CRIPTOMONEDAS REALES ====================
def get_all_cryptos_from_yahoo():
    """Obtiene TODAS las criptomonedas disponibles en Yahoo Finance usando yahooquery"""
    try:
        print("🔄 Obteniendo todas las criptomonedas de Yahoo Finance...")
        s = Screener()
        all_cryptos = []
        seen = set()
        offset = 0
        limit = 100
        
        while True:
            try:
                data = s.get_screeners('all_cryptocurrencies_us', count=limit, offset=offset)
                quotes = data.get('all_cryptocurrencies_us', {}).get('quotes', [])
                
                if not quotes or len(quotes) == 0:
                    print(f"✅ No hay más datos en offset {offset}")
                    break
                
                new_count = 0
                for quote in quotes:
                    symbol = quote.get('symbol', '')
                    if symbol and symbol.endswith('-USD') and symbol not in seen:
                        seen.add(symbol)
                        all_cryptos.append(symbol)
                        new_count += 1
                
                print(f"📦 Offset {offset}: +{new_count} nuevas (total: {len(all_cryptos)})")
                
                if new_count == 0:
                    break
                    
                offset += limit
                
            except Exception as e:
                print(f"❌ Error en offset {offset}: {e}")
                break
        
        print(f"✅ TOTAL CRIPTOMONEDAS ENCONTRADAS: {len(all_cryptos)}")
        
        # Guardar en archivo para debug
        import json
        with open('all_cryptos_debug.json', 'w') as f:
            json.dump(all_cryptos, f, indent=2)
        
        return all_cryptos
        
    except Exception as e:
        print(f"❌ Error obteniendo criptos con yahooquery: {e}")
        # Fallback a lista manual si algo falla
        return [
            "BTC-USD", "ETH-USD", "USDT-USD", "BNB-USD", "SOL-USD",
            "XRP-USD", "USDC-USD", "ADA-USD", "DOGE-USD", "TRX-USD",
            "AVAX-USD", "SHIB-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
            "LTC-USD", "BCH-USD", "NEAR-USD", "UNI-USD", "ATOM-USD"
        ]

# Obtener TODAS las criptomonedas
CRYPTOS = get_all_cryptos_from_yahoo()

# ==================== ACCIONES ====================
STOCKS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "NFLX"]

# Unir todo
SYMBOLS = STOCKS + CRYPTOS

# Nombres legibles (se generan automáticamente para las criptos nuevas)
def generate_crypto_name(symbol):
    """Genera un nombre legible para la criptomoneda"""
    name_map = {
        "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "USDT-USD": "Tether",
        "BNB-USD": "BNB", "SOL-USD": "Solana", "XRP-USD": "Ripple",
        "USDC-USD": "USD Coin", "ADA-USD": "Cardano", "DOGE-USD": "Dogecoin",
        "TRX-USD": "TRON", "AVAX-USD": "Avalanche", "SHIB-USD": "Shiba Inu",
        "DOT-USD": "Polkadot", "LINK-USD": "Chainlink", "MATIC-USD": "Polygon",
        "LTC-USD": "Litecoin", "BCH-USD": "Bitcoin Cash", "NEAR-USD": "NEAR Protocol",
        "UNI-USD": "Uniswap", "ATOM-USD": "Cosmos"
    }
    
    if symbol in name_map:
        return name_map[symbol]
    
    # Si no está en el mapa, generar nombre desde el símbolo
    name = symbol.replace('-USD', '').upper()
    return name

# Construir SYMBOL_NAMES automáticamente
SYMBOL_NAMES = {
    # Acciones
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
    "TSLA": "Tesla", "GOOGL": "Google", "AMZN": "Amazon",
    "META": "Meta", "NFLX": "Netflix",
}

# Agregar todas las criptomonedas
for crypto in CRYPTOS:
    SYMBOL_NAMES[crypto] = generate_crypto_name(crypto)

@app.get("/")
async def root():
    return {
        "message": "Inversor API con TODAS las criptomonedas de Yahoo Finance",
        "total_cryptos": len(CRYPTOS),
        "total_stocks": len(STOCKS),
        "total_symbols": len(SYMBOLS),
        "sample_cryptos": CRYPTOS[:20]
    }

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/symbols")
async def get_symbols():
    """Devuelve la lista de símbolos disponibles"""
    return {
        "symbols": SYMBOLS, 
        "names": SYMBOL_NAMES, 
        "count": len(SYMBOLS),
        "cryptos_count": len(CRYPTOS),
        "stocks_count": len(STOCKS)
    }

@app.get("/api/price/{symbol}")
async def get_price(symbol: str):
    """Obtiene el precio de un símbolo específico"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
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
            hist = ticker.history(period="2d")
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

@app.get("/api/prices/top/{limit}")
async def get_top_prices(limit: int = 50):
    """Obtiene las TOP N criptomonedas por market cap"""
    top_cryptos_data = []
    
    # Solo procesar criptomonedas (no acciones)
    for symbol in CRYPTOS[:100]:  # Limitar a primeras 100 para performance
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get('regularMarketPrice', 0)
            market_cap = info.get('marketCap', 0)
            
            if price and price > 0:
                top_cryptos_data.append({
                    "symbol": symbol.replace('-USD', ''),
                    "name": SYMBOL_NAMES.get(symbol, symbol),
                    "price": round(float(price), 2),
                    "marketCap": market_cap
                })
        except:
            continue
    
    # Ordenar por market cap y limitar
    top_cryptos_data.sort(key=lambda x: x.get('marketCap', 0), reverse=True)
    return {"top_cryptos": top_cryptos_data[:limit], "count": len(top_cryptos_data[:limit])}

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
            dates = [d.strftime("%Y-%m-%d") for d in hist.index.tolist()]
            return {
                "symbol": symbol,
                "name": SYMBOL_NAMES.get(symbol, symbol),
                "prices": prices,
                "dates": dates,
                "count": len(prices)
            }
        else:
            return {"symbol": symbol, "prices": [], "count": 0}
    except Exception as e:
        return {"symbol": symbol, "prices": [], "error": str(e)}

@app.get("/api/cryptos")
async def get_cryptos():
    """Devuelve solo las criptomonedas con precio actual"""
    cryptos_data = []
    
    # Limitar a primeras 200 para no sobrecargar
    for symbol in CRYPTOS[:200]:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                cryptos_data.append({
                    "symbol": symbol.replace('-USD', ''),
                    "name": SYMBOL_NAMES.get(symbol, symbol),
                    "price": round(float(price), 2)
                })
        except:
            pass
    
    return {
        "cryptos": cryptos_data, 
        "count": len(cryptos_data),
        "total_available": len(CRYPTOS)
    }

@app.get("/api/cryptos/all")
async def get_all_cryptos_symbols():
    """Devuelve la lista completa de símbolos de criptomonedas"""
    return {
        "cryptos": CRYPTOS,
        "count": len(CRYPTOS),
        "message": "TODAS las criptomonedas disponibles en Yahoo Finance"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
