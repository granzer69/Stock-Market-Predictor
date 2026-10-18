import { StockDesk } from "@/components/stock-desk"

export default async function Page({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params
  return <StockDesk ticker={decodeURIComponent(symbol)} />
}
