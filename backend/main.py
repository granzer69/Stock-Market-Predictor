from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import joblib
from tensorflow.keras.models import load_model
import random

app = FastAPI()

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model and scaler
model = load_model("stock_predictor_model.h5")
scaler = joblib.load("scaler.save")

# Read CSV once at startup
df = pd.read_csv("top50_stocks_data.csv")

@app.get("/predict")
def predict_price(symbol: str = Query(..., description="Stock symbol like AAPL, MSFT, etc.")):
    stock_data = df[df['Symbol'] == symbol]

    if len(stock_data) < 60:
        return {"error": "Not enough data for prediction."}

    stock_data = stock_data.sort_values(by='Date')
    close_prices = stock_data['Close'].values[-60:].reshape(-1, 1)
    close_prices_scaled = scaler.transform(close_prices)

    X_test = np.array([close_prices_scaled])
    X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

    predicted_scaled_price = model.predict(X_test)
    predicted_price = scaler.inverse_transform(predicted_scaled_price)

    return {
        "symbol": symbol,
        "predicted_price": float(predicted_price[0][0]),
        "confidence": round(random.uniform(0.7, 0.95), 2)  # Dummy confidence for frontend
    }

@app.get("/chart")
def get_chart_data(symbol: str = Query(..., description="Stock symbol like AAPL, MSFT, etc.")):
    stock_data = df[df['Symbol'] == symbol]

    if len(stock_data) < 60:
        return {"error": "Not enough data for chart."}

    stock_data = stock_data.sort_values(by='Date')
    stock_data = stock_data.tail(60)

    chart_data = [
        {"date": row["Date"], "price": row["Close"]}
        for _, row in stock_data.iterrows()
    ]

    return {"symbol": symbol, "chart_data": chart_data}

@app.get("/realtime")
def get_realtime_data(symbol: str = Query(..., description="Stock symbol like AAPL, MSFT, etc.")):
    stock_data = df[df['Symbol'] == symbol].sort_values(by='Date')

    if len(stock_data) == 0:
        return {"error": "Stock symbol not found."}

    latest_row = stock_data.iloc[-1]
    previous_row = stock_data.iloc[-2]

    price = latest_row['Close']
    previous_close = previous_row['Close']

    # Simulate slight price fluctuation (for demo purposes)
    simulated_change = random.uniform(-1, 1)
    simulated_price = round(price + simulated_change, 2)

    change = round(simulated_price - previous_close, 2)
    change_percent = round((change / previous_close) * 100, 2)

    return {
        "symbol": symbol,
        "price": simulated_price,
        "change": change,
        "change_percent": change_percent,
        "previous_close": previous_close
    }
