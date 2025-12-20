/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  webpack: (config) => {
    config.ignoreWarnings = [{ module: /node_modules/, message: /sourceMapURL/ }]
    return config
  },
  turbopack: {},
}

export default nextConfig
