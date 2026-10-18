import type React from "react"
import "./globals.css"
import type { Metadata } from "next"
import { Inter } from "next/font/google"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "NSE Trading Desk — Paper Research",
  description:
    "Nifty 50 paper-trading research desk: evaluation, backtest, and ML predictions (INR). Not investment advice.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-900`}>{children}</body>
    </html>
  )
}
