import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    env: {
    NEXT_PUBLIC_NEO4J_URI: process.env.NEO4J_URI,
    NEXT_PUBLIC_NEO4J_USER: process.env.NEO4J_USER,
    NEXT_PUBLIC_NEO4J_PASSWORD: process.env.NEO4J_PASSWORD,
  },
};

export default nextConfig;
