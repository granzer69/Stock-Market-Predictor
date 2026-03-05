import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import joblib
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

# 💾 Load Model & Scaler with Error Handling
model_path = "stock_predictor_model.h5"
scaler_path = "scaler.save"

if not os.path.exists(model_path) or not os.path.exists(scaler_path):
    st.error("❌ Model or Scaler file not found! Please ensure 'stock_predictor_model.h5' and 'scaler.save' are in the app directory.")
    st.stop()

model = load_model(model_path)
scaler = joblib.load(scaler_path)

# 🏄‍♂️ Gen-Z Style Title
st.markdown("<h1 style='color:#FF4B4B;text-align:center;'>🔥 Gen-Z Stock Price Predictor 🔥</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#4CAF50;text-align:center;'>Upload your CSV file & get stock vibes! 📈😎🚀</p>", unsafe_allow_html=True)

# 📁 File Uploader
uploaded_file = st.file_uploader("Upload your Stock CSV file (must have 'Close' column):", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("✅ File Uploaded Successfully!")
    st.write("### 🔍 Data Preview:")
    st.dataframe(df.head())

    if 'Close' not in df.columns:
        st.error("❌ 'Close' column missing! Please upload a valid stock CSV file.")
    elif len(df) < 60:
        st.warning("⚠️ Not enough data! Need at least 60 rows for prediction.")
    else:
        # 📊 Price Trend Plot
        st.subheader("📈 Stock Close Price Trend")
        fig, ax = plt.subplots(figsize=(10,4))
        ax.plot(df['Close'], color='skyblue', linewidth=2)
        ax.set_title("Close Price Over Time", fontsize=14)
        ax.set_xlabel("Days")
        ax.set_ylabel("Close Price (USD)")
        ax.grid(True)
        st.pyplot(fig)

        # 🧠 Predict Next Day Price
        data = df.filter(['Close'])
        dataset = data.values
        last_60_days = dataset[-60:]
        last_60_days_scaled = scaler.transform(last_60_days)

        X_test = np.array([last_60_days_scaled])
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

        pred_price = model.predict(X_test)
        pred_price = scaler.inverse_transform(pred_price)

        st.markdown(f"<h2 style='color:#FF4B4B;text-align:center;'>🚀 Predicted Next Day Price: <span style='color:#4CAF50;'>${pred_price[0][0]:.2f}</span></h2>", unsafe_allow_html=True)

else:
    st.info("👈 Upload a CSV file to get started!")
