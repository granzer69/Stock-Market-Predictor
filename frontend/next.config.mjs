/** @type {import('next').NextConfig} */
const apiOrigin = process.env.API_ORIGIN || "http://127.0.0.1:8000"

const nextConfig = {
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
