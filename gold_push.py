import requests
import pandas as pd
import time
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands
import os

# 获取环境变量
OANDA_TOKEN = os.environ.get("OANDA_TOKEN")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN")
SYMBOL = "XAU_USD"

headers = {
    'Authorization': f'Bearer {OANDA_TOKEN}'
}

def wx_push(title, content):
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "markdown"
    }
    try:
        requests.post(url, json=data)
    except Exception as e:
        print(f"微信推送失败：{e}")

def fetch_candles(symbol, count=150, granularity="M1"):
    url = f"https://api-fxpractice.oanda.com/v3/instruments/{symbol}/candles"
    params = {
        "count": count,
        "granularity": granularity,
        "price": "M"
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    candles = [
        {
            "time": c["time"],
            "open": float(c["mid"]["o"]),
            "high": float(c["mid"]["h"]),
            "low": float(c["mid"]["l"]),
            "close": float(c["mid"]["c"])
        }
        for c in data["candles"]
    ]
    return pd.DataFrame(candles)

def detect_signals(df):
    close = df['close']
    df['rsi'] = RSIIndicator(close).rsi()
    macd = MACD(close)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()
    bb = BollingerBands(close)
    df['bb_mid'] = bb.bollinger_mavg()

    latest = df.iloc[-1]
    previous = df.iloc[-2]
    signals = []

    # 必胜空单
    if (
        latest['close'] < latest['bb_mid'] and
        latest['macd'] < latest['macd_signal'] and
        latest['macd_diff'] < 0 and
        latest['rsi'] > 60 and
        previous['rsi'] > latest['rsi']
    ):
        signals.append({
            "type": "必胜空单",
            "entry": round(latest['close'], 2),
            "sl": round(latest['close'] + 13, 2),
            "tp": round(latest['close'] - 15, 2)
        })

    # 必胜多单
    if (
        latest['close'] > latest['bb_mid'] and
        latest['macd'] > latest['macd_signal'] and
        latest['macd_diff'] > 0 and
        latest['rsi'] < 40 and
        previous['rsi'] < latest['rsi']
    ):
        signals.append({
            "type": "必胜多单",
            "entry": round(latest['close'], 2),
            "sl": round(latest['close'] - 13, 2),
            "tp": round(latest['close'] + 15, 2)
        })

    # 平时空单
    if (
        latest['macd'] < latest['macd_signal'] and
        latest['rsi'] > 60 and
        latest['close'] < latest['bb_mid']
    ):
        signals.append({
            "type": "平时空单",
            "entry": round(latest['close'], 2),
            "sl": round(latest['close'] + 12, 2),
            "tp": round(latest['close'] - 14, 2)
        })

    # 平时多单
    if (
        latest['macd'] > latest['macd_signal'] and
        latest['rsi'] > 40 and
        latest['close'] > latest['bb_mid']
    ):
        signals.append({
            "type": "平时多单",
            "entry": round(latest['close'], 2),
            "sl": round(latest['close'] - 12, 2),
            "tp": round(latest['close'] + 14, 2)
        })

    return signals

def main():
    print("系统启动...")
    while True:
        try:
            df = fetch_candles(SYMBOL)
            signals = detect_signals(df)
            for sig in signals:
                content = f"{sig['type']} | 入场: {sig['entry']} | 止损: {sig['sl']} | 止盈: {sig['tp']}"
                wx_push(f"{SYMBOL.replace('_','')} {sig['type']}", content)
                print("推送成功:", content)
        except Exception as e:
            print("错误:", e)

        time.sleep(60)

if __name__ == "__main__":
    main()
