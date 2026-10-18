"""
Streamlit demo: NSE quotes via Yahoo Finance (.NS tickers), prices in INR.

No API keys required. Optional local Keras model prediction if
stock_predictor_model.h5 and scaler.save exist beside this file.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="NSE Yahoo Finance Demo", layout="wide")

st.markdown(
    "<h1 style='text-align:center;'>🇮🇳 NSE stock snapshot (Yahoo Finance)</h1>",
    unsafe_allow_html=True,
)
st.caption("Uses public Yahoo Finance data for `.NS` tickers. Not investment advice.")

symbol = st.text_input("NSE symbol", value="RELIANCE").strip().upper().replace(".NS", "")
yahoo = f"{symbol}.NS"

if st.button("Fetch & chart"):
    hist = yf.Ticker(yahoo).history(period="3mo", auto_adjust=True)
    if hist.empty or len(hist) < 2:
        st.error(f"No data for {yahoo}. Check the symbol.")
        st.stop()

    hist = hist.tail(60)
    latest = float(hist["Close"].iloc[-1])
    prev = float(hist["Close"].iloc[-2])
    change = latest - prev
    pct = (change / prev) * 100 if prev else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Latest close", f"₹{latest:,.2f}", f"{change:+.2f}")
    c2.metric("% change", f"{pct:+.2f}%")
    c3.metric("Bars shown", str(len(hist)))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(hist.index, hist["Close"], color="#2563eb", linewidth=2)
    ax.set_title(f"{symbol} — last {len(hist)} closes (INR)")
    ax.set_ylabel("Price (₹)")
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

    model_path = Path("stock_predictor_model.h5")
    scaler_path = Path("scaler.save")
    if model_path.exists() and scaler_path.exists():
        import joblib
        from tensorflow.keras.models import load_model

        if len(hist) >= 60:
            model = load_model(model_path)
            scaler = joblib.load(scaler_path)
            window = hist["Close"].values[-60:].reshape(-1, 1)
            scaled = scaler.transform(window)
            x = np.reshape(scaled, (1, 60, 1))
            pred = scaler.inverse_transform(model.predict(x, verbose=0))[0][0]
            st.success(f"Model next-close hint: ₹{float(pred):,.2f}")
        else:
            st.info("Need at least 60 closes for optional model prediction.")
    else:
        st.info("Add stock_predictor_model.h5 and scaler.save for an optional LSTM hint.")

else:
    st.info("Enter an NSE symbol (e.g. RELIANCE, TCS) and click **Fetch & chart**.")
