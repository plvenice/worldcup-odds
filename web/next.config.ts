import type { NextConfig } from "next";

// BASE_PATH is set only for the GitHub Pages build (served from /worldcup-odds).
// On Vercel it is unset, so the site serves from the domain root.
const basePath = process.env.BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  basePath,
  images: { unoptimized: true },
};

export default nextConfig;
