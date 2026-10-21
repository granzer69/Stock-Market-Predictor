import { NextRequest, NextResponse } from "next/server"

export const config = {
  // Proxy API traffic only. Do not match /evaluation or /backtest — those are Next.js pages.
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
