import ccxt
import pandas as pd
import requests
import time
import os
from flask import Flask
import threading
from datetime import datetime

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = '8835400649:AAFQACEy69cYk_1LkRdqmRUWgLWZhl6gv8M'
TELEGRAM_CHAT_ID = '8653843379'

# 18 Pares vigilados
PARES = [
    'NEAR/USDT', 'AAVE/USDT', 'AVAX/USDT', 'INJ/USDT', 'LTC/USDT', 
    'UNI/USDT', 'PUMP/USDT', 'OP/USDT', 'SOL/USDT', 'DOGE/USDT', 
    'PEPE/USDT', 'ARB/USDT', 'LINK/USDT', 'FIL/USDT', 'APT/USDT',
    'HYPE/USDT', 'ZEC/USDT', 'ADA/USDT'
]

TIMEFRAMES = ['1h', '4h']
SWING_LOOKBACK = 10
SL_PCT = 0.02
TP_PCT = 0.05

exchange = ccxt.binance({'enableRateLimit': True})
app = Flask(__name__)

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def get_ohlcv(symbol, timeframe):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        print(f"Error obteniendo datos de {symbol}: {e}")
        return None

def detectar_smc(df, timeframe, symbol):
    if df is None or len(df) < SWING_LOOKBACK + 5:
        return []
    
    alertas = []
    df['swing_high'] = df['high'].rolling(window=SWING_LOOKBACK).max().shift(1)
    df['swing_low'] = df['low'].rolling(window=SWING_LOOKBACK).min().shift(1)
    
    idx = -2
    vela = df.iloc[idx]
    entry_price = vela['close']
    
    if vela['low'] <= df['swing_low'].iloc[idx] and vela['close'] > df['swing_low'].iloc[idx]:
        sl_price = entry_price * (1 - SL_PCT)
        tp_price = entry_price * (1 + TP_PCT)
        alertas.append(f"🚨 *SEÑAL SMC: {symbol}* 🚨\nTimeframe: {timeframe.upper()}\n\n🟢 *Dirección: LONG*\n💰 Entrada: ${entry_price:.4f}\n🛑 SL (2%): ${sl_price:.4f}\n🎯 TP (5%): ${tp_price:.4f}\n\n📝 *Motivo:* Liquidity Sweep en mínimos.")

    elif vela['high'] >= df['swing_high'].iloc[idx] and vela['close'] < df['swing_high'].iloc[idx]:
        sl_price = entry_price * (1 + SL_PCT)
        tp_price = entry_price * (1 - TP_PCT)
        alertas.append(f"🚨 *SEÑAL SMC: {symbol}* 🚨\nTimeframe: {timeframe.upper()}\n\n🔴 *Dirección: SHORT*\n💰 Entrada: ${entry_price:.4f}\n🛑 SL (2%): ${sl_price:.4f}\n🎯 TP (5%): ${tp_price:.4f}\n\n📝 *Motivo:* Liquidity Sweep en máximos.")

    return alertas

def escanear_mercado():
    while True:
        for par in PARES:
            for tf in TIMEFRAMES:
                df = get_ohlcv(par, tf)
                alertas = detectar_smc(df, tf, par)
                if alertas:
                    for msg in alertas:
                        enviar_telegram(msg)
                        print(f"✅ Señal enviada: {par} en {tf}")
        time.sleep(900)

def enviar_estado_cada_hora():
    time.sleep(10)
    while True:
        hora_actual = datetime.now().strftime('%H:%M')
        msg = f"⚙️ *Bot Activo* - {hora_actual}\nVigilando {len(PARES)} pares en 1H y 4H. Sistema operativo."
        enviar_telegram(msg)
        print(f"⏰ Mensaje de estado enviado: {hora_actual}")
        time.sleep(3600)

@app.route('/')
def home():
    return "✅ Bot SMC de Joselito corriendo en la nube."

if __name__ == "__main__":
    bot_thread = threading.Thread(target=escanear_mercado, daemon=True)
    bot_thread.start()
    
    estado_thread = threading.Thread(target=enviar_estado_cada_hora, daemon=True)
    estado_thread.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
