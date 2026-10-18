import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { SiteHeader } from "@/components/site-header"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Bharat Desk — NSE Paper Research",
  description:
    "Nifty 50 desk with world tape, LightGBM forecasts, evaluation baselines, and ₹10L paper book. Not investment advice.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-[#07090d] text-[#e7eef7] antialiased`}>
        <SiteHeader />
        {children}
      </body>
    </html>
  )
}
