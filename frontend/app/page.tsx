"use client";

import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ArrowUpIcon, ArrowDownIcon } from "lucide-react";

const top50Stocks = [
  "AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "META", "NVDA", "BRK.B", "UNH", "V",
  "JNJ", "JPM", "XOM", "PG", "MA", "HD", "CVX", "LLY", "PFE", "ABBV",
  "KO", "MRK", "PEP", "DIS", "BAC", "VZ", "ADBE", "CSCO", "NFLX", "INTC",
  "CRM", "ORCL", "T", "NKE", "WMT", "MCD", "IBM", "QCOM", "HON", "ABT",
  "AVGO", "TXN", "COST", "PYPL", "AMD", "LIN", "CAT", "UPS", "GE", "BA"
];

export default function StockDashboard() {
  const [selectedStock, setSelectedStock] = useState("AAPL");
  const [prediction, setPrediction] = useState<number | null>(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState('');

  const [stockData, setStockData] = useState({
    symbol: "AAPL",
    price: 0,
    change: 0,
    changePercent: 0,
    previousClose: 0,
  });

  const [aiPrediction, setAiPrediction] = useState({
    nextDayPrice: 0,
    confidence: 0,
  });

  useEffect(() => {
    setLoading(true);

    fetch(`http://localhost:8000/realtime?symbol=${selectedStock}`)
      .then(res => res.json())
      .then(data => {
        if (data) {
          setStockData({
            symbol: data.symbol,
            price: data.price,
            change: data.change,
            changePercent: data.change_percent,
            previousClose: data.previous_close,
          });
        }
        setLoading(false);
      });

    fetch(`http://localhost:8000/predict?symbol=${selectedStock}`)
      .then(res => res.json())
      .then(data => {
        if (data.predicted_price) {
          setAiPrediction({
            nextDayPrice: data.predicted_price,
            confidence: data.confidence,
          });
        }
      });

    fetch(`http://localhost:8000/chart?symbol=${selectedStock}`)
      .then(res => res.json())
      .then(data => {
        if (data.chart_data) {
          setChartData(data.chart_data);
        }
      });
  }, [selectedStock]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <div className="container mx-auto px-4 py-8">

        <header className="mb-8 text-center">
          <h1 className="text-4xl font-extrabold bg-gradient-to-r from-blue-400 to-purple-600 text-transparent bg-clip-text">
            AI-Powered Stock Market Predictor
          </h1>
        </header>

        <div className="max-w-xs mx-auto mb-8">
          <select
            value={selectedStock}
            onChange={(e) => setSelectedStock(e.target.value)}
            className="w-full p-3 rounded bg-gray-800 text-white border border-gray-600 focus:outline-none"
          >
            {top50Stocks.map((stock) => (
              <option key={stock} value={stock}>{stock}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700">
            <h2 className="text-xl font-semibold text-gray-400 mb-2">Real-Time Price</h2>
            <h3 className="text-2xl font-bold">{selectedStock}</h3>
            <div className="mt-2 text-5xl font-bold tracking-tighter">${stockData.price.toFixed(2)}</div>
            <div className="flex mt-2 items-center">
              {stockData.change >= 0 ? (
                <span className="text-green-500 flex items-center">
                  <ArrowUpIcon className="w-5 h-5 mr-1" /> {stockData.change} ({stockData.changePercent}%)
                </span>
              ) : (
                <span className="text-red-500 flex items-center">
                  <ArrowDownIcon className="w-5 h-5 mr-1" /> {Math.abs(stockData.change)} ({Math.abs(stockData.changePercent)}%)
                </span>
              )}
            </div>
            <div className="text-sm text-gray-400 mt-2">Last updated: {currentTime}</div>
          </div>

          <div className="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700">
            <h2 className="text-xl font-semibold text-gray-400 mb-2">AI Predicted Price</h2>
            <h3 className="text-2xl font-bold">Next Trading Day</h3>
            <div className="mt-2 text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-600">
              ${loading ? "..." : aiPrediction.nextDayPrice.toFixed(2)}
            </div>
            <div className="mt-4 flex items-center">
              <div className="w-full bg-gray-700 rounded-full h-2.5">
                <div
                  className="bg-blue-600 h-2.5 rounded-full"
                  style={{ width: `${aiPrediction.confidence * 100}%` }}
                ></div>
              </div>
              <span className="ml-2 text-sm text-gray-400">{(aiPrediction.confidence * 100).toFixed(0)}% confidence</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700">
          <h2 className="text-xl font-semibold mb-6">Stock Price Trend (Last 60 Days)</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" />
                <Tooltip contentStyle={{ backgroundColor: "#1F2937", borderColor: "#374151", color: "#F9FAFB" }} />
                <Legend />
                <Line type="monotone" dataKey="price" stroke="#3B82F6" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
