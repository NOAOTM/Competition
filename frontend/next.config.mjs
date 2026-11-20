/** @type {import('next').NextConfig} */
const backend = process.env.BACKEND_API_URL || "http://backend:8000";
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};
export default nextConfig;
