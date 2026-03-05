import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import joblib
import finnhub
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import os
import time

# Set page config
st.set_page_config(page_title="FinTech Stock Predictor", layout="wide")

# Load Model & Scaler
model = load_model("stock_predictor_model.h5")
scaler = joblib.load('scaler.save')

# Finnhub API
api_key = 'd15h9k1r01qhqto5r8r0d15h9k1r01qhqto5r8rg'  # Replace with your actual Finnhub API key
finnhub_client = finnhub.Client(api_key=api_key)

st.markdown("<h1 style='color:#FF4B4B;text-align:center;'>🔥 FinTech Grade Real-Time Stock Predictor 🔥</h1>", unsafe_allow_html=True)

# User input
ticker = st.text_input("Enter Stock Symbol (e.g., AAPL, MSFT, TSLA):", value="AAPL")

if st.button("Predict Now"):
    try:
        end_time = int(time.time())
        start_time = end_time - (60 * 86400)  # last 60 days in seconds

        res = finnhub_client.stock_candles(ticker, 'D', start_time, end_time)

        if res and 'c' in res and len(res['c']) >= 60:
            closes = res['c'][-60:]
            highs = res['h'][-60:]
            lows = res['l'][-60:]
            opens = res['o'][-60:]
            volumes = res['v'][-60:]

            # Display real-time summary stats
            latest_close = closes[-1]
            prev_close = closes[-2]
            change = latest_close - prev_close
            pct_change = (change / prev_close) * 100

            col1, col2, col3 = st.columns(3)
            col1.metric("📈 Latest Close", f"${latest_close:.2f}", f"{change:.2f} USD")
            col2.metric("📊 % Change", f"{pct_change:.2f}%", delta_color="normal" if pct_change >=0 else "inverse")
            col3.metric("🕒 Volume", f"{volumes[-1]:,.0f}")

            # Plot Candlestick Chart using Plotly
            fig = go.Figure(data=[go.Candlestick(
                x=pd.to_datetime(res['t'], unit='s'),
                open=opens,
                high=highs,
                low=lows,
                close=closes
            )])
            fig.update_layout(title=f"{ticker} - Last 60 Days Candlestick Chart",
                              xaxis_title='Date', yaxis_title='Price (USD)',
                              template='plotly_dark', width=1000, height=500)
            st.plotly_chart(fig)

            # Predict Next Day Price
            last_60_days = np.array(closes).reshape(-1, 1)
            last_60_days_scaled = scaler.transform(last_60_days)

            X_test = np.array([last_60_days_scaled])
            X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

            pred_price = model.predict(X_test)
            pred_price = scaler.inverse_transform(pred_price)

            st.markdown(f"<h2 style='color:#4CAF50;text-align:center;'>🚀 Predicted Next Close Price for {ticker}: <span style='color:#FF4B4B;'>${pred_price[0][0]:.2f}</span></h2>", unsafe_allow_html=True)

        else:
            st.error("❌ Not enough data fetched from Finnhub!")

    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.info("👈 Enter a ticker symbol & hit Predict Now!")
