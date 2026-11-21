/** @type {import('next').NextConfig} */
const backend = process.env.BACKEND_API_URL || "http://backend:8000";
const photocraft = process.env.PHOTOCRAFT_URL || "http://photocraft:8080";
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/photocraft", destination: `${photocraft}/` },
      { source: "/photocraft/:path*", destination: `${photocraft}/:path*` },
    ];
  },
};
export default nextConfig;
