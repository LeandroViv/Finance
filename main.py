from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from datetime import datetime, timedelta
from yahooquery import Screener
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== OBTENER TODAS LAS CRIPTOMONEDAS REALES ====================
def get_backup_cryptos():
    """Lista de respaldo de las criptomonedas más importantes"""
    return [
        "BTC-USD", "ETH-USD", "USDT-USD", "BNB-USD", "SOL-USD",
        "XRP-USD", "USDC-USD", "ADA-USD", "DOGE-USD", "TRX-USD",
        "AVAX-USD", "SHIB-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
        "LTC-USD", "BCH-USD", "NEAR-USD", "UNI-USD", "ATOM-USD",
        "ETC-USD", "XLM-USD", "ICP-USD", "FIL-USD", "APT-USD",
        "HBAR-USD", "ARB-USD", "VET-USD", "QNT-USD", "MKR-USD",
        "RNDR-USD", "GRT-USD", "AAVE-USD", "ALGO-USD", "EGLD-USD"
    ]

def get_all_cryptos_from_yahoo():
    """Obtiene TODAS las criptomonedas disponibles en Yahoo Finance usando yahooquery"""
    try:
        print("🔄 Obteniendo todas las criptomonedas de Yahoo Finance...")
        s = Screener()
        all_cryptos = []
        seen = set()
        
        # Intentar obtener sin paginación
        try:
            data = s.get_screeners('all_cryptocurrencies_us')
            quotes = data.get('all_cryptocurrencies_us', {}).get('quotes', [])
            
            for quote in quotes:
                symbol = quote.get('symbol', '')
                if symbol and symbol.endswith('-USD') and symbol not in seen:
                    seen.add(symbol)
                    all_cryptos.append(symbol)
            
            print(f"✅ Obtenidas {len(all_cryptos)} criptomonedas")
            
        except Exception as e:
            print(f"❌ Error con método simple: {e}")
            return get_backup_cryptos()
        
        if len(all_cryptos) == 0:
            print("⚠️ No se encontraron criptomonedas, usando lista de respaldo")
            return get_backup_cryptos()
        
        print(f"✅ TOTAL CRIPTOMONEDAS ENCONTRADAS: {len(all_cryptos)}")
        
        # Guardar en archivo para debug
        with open('all_cryptos_debug.json', 'w') as f:
            json.dump(all_cryptos, f, indent=2)
        
        return all_cryptos
        
    except Exception as e:
        print(f"❌ Error obteniendo criptos con yahooquery: {e}")
        return get_backup_cryptos()

# Obtener TODAS las criptomonedas
CRYPTOS = get_all_cryptos_from_yahoo()

# ==================== ACCIONES ====================
STOCKS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "NFLX"]

# Unir todo
SYMBOLS = STOCKS + CRYPTOS

# Nombres legibles
def generate_crypto_name(symbol):
    """Genera un nombre legible para la criptomoneda"""
    name_map = {
        "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "USDT-USD": "Tether",
        "BNB-USD": "BNB", "SOL-USD": "Solana", "XRP-USD": "Ripple",
        "USDC-USD": "USD Coin", "ADA-USD": "Cardano", "DOGE-USD": "Dogecoin",
        "TRX-USD": "TRON", "AVAX-USD": "Avalanche", "SHIB-USD": "Shiba Inu",
        "DOT-USD": "Polkadot", "LINK-USD": "Chainlink", "MATIC-USD": "Polygon",
        "LTC-USD": "Litecoin", "BCH-USD": "Bitcoin Cash", "NEAR-USD": "NEAR Protocol",
        "UNI-USD": "Uniswap", "ATOM-USD": "Cosmos", "ETC-USD": "Ethereum Classic",
        "XLM-USD": "Stellar", "ICP-USD": "Internet Computer", "FIL-USD": "Filecoin",
        "APT-USD": "Aptos", "HBAR-USD": "Hedera", "ARB-USD": "Arbitrum",
        "VET-USD": "VeChain", "QNT-USD": "Quant", "MKR-USD": "Maker",
        "RNDR-USD": "Render", "GRT-USD": "The Graph", "AAVE-USD": "Aave",
        "ALGO-USD": "Algorand", "EGLD-USD": "MultiversX"
    }
    
    if symbol in name_map:
        return name_map[symbol]
    
    name = symbol.replace('-USD', '').upper()
    return name

# Construir SYMBOL_NAMES
SYMBOL_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
    "TSLA": "Tesla", "GOOGL": "Google", "AMZN": "Amazon",
    "META": "Meta", "NFLX": "Netflix",
}

for crypto in CRYPTOS:
    SYMBOL_NAMES[crypto] = generate_crypto_name(crypto)

# ==================== ENDPOINTS ====================
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
    return {
        "symbols": SYMBOLS, 
        "names": SYMBOL_NAMES, 
        "count": len(SYMBOLS),
        "cryptos_count": len(CRYPTOS),
        "stocks_count": len(STOCKS)
    }

@app.get("/api/price/{symbol}")
async def get_price(symbol: str):
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
    """Obtiene todos los precios actuales - Formato para el frontend"""
    results = {}
    for symbol in SYMBOLS[:50]:  # Limitamos a 50 para performance
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
            results[symbol] = None
    return results

@app.get("/api/prices/simple")
async def get_all_prices_simple():
    """Obtiene todos los precios actuales - Formato simple (solo números)"""
    results = {}
    for symbol in SYMBOLS[:50]:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                results[symbol] = round(float(price), 2)
            else:
                results[symbol] = None
        except Exception as e:
            results[symbol] = None
    return results

@app.get("/api/historical")
async def get_historical(
    symbol: str = Query(...),
    days: int = Query(60)
):
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
        return {"symbol": symbol, "prices": [], "count": 0}
    except Exception as e:
        return {"symbol": symbol, "prices": [], "error": str(e)}

@app.get("/api/cryptos")
async def get_cryptos():
    cryptos_data = []
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
    return {
        "cryptos": CRYPTOS,
        "count": len(CRYPTOS)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
