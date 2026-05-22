from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from datetime import datetime, timedelta
import json
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== OBTENER TODAS LAS CRIPTOMONEDAS CON PRECIO ====================
def get_all_cryptos_with_price():
    """Detecta automáticamente todas las criptomonedas con precio en Yahoo Finance"""
    print("🔄 Escaneando todas las criptomonedas en Yahoo Finance...")
    
    # Lista extensa de posibles criptomonedas (combinación de símbolos comunes)
    crypto_symbols_base = [
        # TOP 100 por market cap
        "BTC", "ETH", "USDT", "BNB", "XRP", "USDC", "SOL", "ADA", "DOGE", "TRX",
        "AVAX", "SHIB", "DOT", "LINK", "MATIC", "LTC", "BCH", "NEAR", "UNI", "ATOM",
        "ETC", "XLM", "ICP", "FIL", "APT", "HBAR", "ARB", "VET", "QNT", "MKR",
        "RNDR", "GRT", "AAVE", "ALGO", "EGLD", "SAND", "MANA", "GALA", "AXS", "EOS",
        "XTZ", "KSM", "ZEC", "DASH", "FLR", "ENJ", "CHZ", "CRO", "FTM", "THETA",
        "SNX", "SUSHI", "YFI", "COMP", "BAT", "ZIL", "NEO", "ONT", "OMG", "WAVES",
        "KAVA", "RUNE", "ONE", "STX", "ANKR", "CRV", "1INCH", "CELO", "BAL", "BAND",
        "KLAY", "MINA", "OSMO", "QTUM", "REN", "SKL", "ALICE", "AUDIO", "BNT", "C98",
        "CTSI", "DYDX", "ENS", "FET", "FLOW", "GNO", "HNT", "ILV", "KNC", "LDO",
        "LRC", "MASK", "OCEAN", "PEOPLE", "REQ", "RLY", "STORJ", "SUPER", "SYN", "UMA",
        # Criptos adicionales
        "ACH", "AGLD", "ALPHA", "API3", "AR", "ASM", "AST", "BADGER", "BICO", "BLZ",
        "CVC", "DENT", "DESO", "DKA", "DYDX", "ELA", "ERN", "FARM", "FORTH", "FOX",
        "GTC", "GUSD", "ICP", "IDEX", "INJ", "IOTX", "JASMY", "JOE", "KRL", "LIT",
        "LOKA", "MAGIC", "MATH", "MDT", "MEDIA", "METIS", "MIR", "MKR", "MLN", "MNDE",
        "MOB", "MXC", "MYTH", "NKN", "NMR", "NULS", "OXT", "PHA", "PUNDIX", "PYR",
        "RAD", "RAY", "RBN", "RLC", "ROSE", "RSR", "SGB", "SKL", "SLP", "SPELL",
        "SUI", "SUPER", "SXP", "TRB", "TRIBE", "TWT", "UMA", "UNFI", "VTHO", "WOO"
    ]
    
    all_cryptos = []
    verified_cryptos = []
    
    print(f"📊 Verificando {len(crypto_symbols_base)} posibles criptomonedas...")
    
    for i, base_symbol in enumerate(crypto_symbols_base):
        symbol = f"{base_symbol}-USD"
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", progress=False)
            
            if not hist.empty:
                last_price = hist['Close'].iloc[-1]
                if last_price and last_price > 0:
                    verified_cryptos.append(symbol)
                    print(f"✅ {i+1}/{len(crypto_symbols_base)}: {symbol} - ${last_price:.4f}")
                else:
                    print(f"⚠️ {i+1}/{len(crypto_symbols_base)}: {symbol} - sin precio")
            else:
                print(f"❌ {i+1}/{len(crypto_symbols_base)}: {symbol} - no encontrada")
                
        except Exception as e:
            print(f"❌ {i+1}/{len(crypto_symbols_base)}: {symbol} - error")
        
        # Pequeña pausa para no sobrecargar la API
        if (i + 1) % 10 == 0:
            time.sleep(0.5)
    
    print(f"\n✅ TOTAL CRIPTOMONEDAS CON PRECIO: {len(verified_cryptos)}")
    
    # Guardar lista completa en archivo
    with open('all_cryptos_with_price.json', 'w') as f:
        json.dump(verified_cryptos, f, indent=2)
    
    # Si no encontró ninguna, usar lista de respaldo
    if len(verified_cryptos) == 0:
        print("⚠️ No se encontraron criptos, usando lista de respaldo")
        return get_backup_cryptos()
    
    return verified_cryptos

def get_backup_cryptos():
    """Lista de respaldo de las criptomonedas principales"""
    return [
        "BTC-USD", "ETH-USD", "USDT-USD", "BNB-USD", "SOL-USD",
        "XRP-USD", "USDC-USD", "ADA-USD", "DOGE-USD", "TRX-USD",
        "AVAX-USD", "SHIB-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
        "LTC-USD", "BCH-USD", "NEAR-USD", "UNI-USD", "ATOM-USD",
        "ETC-USD", "XLM-USD", "ICP-USD", "FIL-USD", "APT-USD",
        "HBAR-USD", "ARB-USD", "VET-USD", "QNT-USD", "MKR-USD"
    ]

# Ejecutar la detección de criptos
print("🚀 Iniciando API - Detectando criptomonedas...")
CRYPTOS = get_all_cryptos_with_price()
print(f"📊 Finalizado: {len(CRYPTOS)} criptomonedas disponibles")

# ==================== ACCIONES ====================
STOCKS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "NFLX"]

# Unir todo
SYMBOLS = STOCKS + CRYPTOS

# Nombres legibles
def generate_crypto_name(symbol):
    """Genera un nombre legible para la criptomoneda"""
    symbol_clean = symbol.replace('-USD', '')
    name_map = {
        "BTC": "Bitcoin", "ETH": "Ethereum", "USDT": "Tether", "BNB": "BNB",
        "SOL": "Solana", "XRP": "Ripple", "USDC": "USD Coin", "ADA": "Cardano",
        "DOGE": "Dogecoin", "TRX": "TRON", "AVAX": "Avalanche", "SHIB": "Shiba Inu",
        "DOT": "Polkadot", "LINK": "Chainlink", "MATIC": "Polygon", "LTC": "Litecoin",
        "BCH": "Bitcoin Cash", "NEAR": "NEAR Protocol", "UNI": "Uniswap", "ATOM": "Cosmos"
    }
    return name_map.get(symbol_clean, symbol_clean)

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
    for symbol in SYMBOLS[:100]:  # Limitamos a 100 para performance
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
