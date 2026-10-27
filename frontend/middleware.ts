import { NextRequest, NextResponse } from "next/server"

export const config = {
  // Documents at /evaluation and /backtest stay on Next.
  // Those pages fetch /api/evaluation and /api/legacy/backtest, which this matcher proxies.
  matcher: ["/api/:path*"],
}

export function middleware(request: NextRequest) {
  const apiOrigin = process.env.API_ORIGIN?.replace(/\/$/, "")
  if (!apiOrigin && !process.env.VERCEL) {
    return NextResponse.next()
  }
  if (!apiOrigin) {
    return NextResponse.json(
      {
        detail:
          "API_ORIGIN is not configured on Vercel. Host the FastAPI backend (see DEPLOY.md) and set API_ORIGIN to its HTTPS base URL, then redeploy.",
      },
      { status: 503 },
    )
  }
  const path = request.nextUrl.pathname + request.nextUrl.search
  return NextResponse.rewrite(new URL(path, `${apiOrigin}/`))
}
