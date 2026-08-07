# syntax=docker/dockerfile:1
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
# NEXT_PUBLIC_* vars are inlined into the client bundle at build time, not
# read from the runtime environment — a value only set on the runner stage
# (or in docker-compose's `environment:`) never reaches the browser. Must be
# passed as a build ARG (see docker-compose.yml's `build.args`).
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID=""
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID
ARG NEXT_PUBLIC_CURRENCY="USD"
ENV NEXT_PUBLIC_CURRENCY=$NEXT_PUBLIC_CURRENCY
# next.config.ts's rewrites() destination is resolved once, here, during the
# build (Next bakes the resolved rewrite rules into the routes manifest — it
# is NOT re-read from the runtime environment on every request). It must
# therefore match the runner stage's value below, or every /api/* rewrite
# targets whatever the process.env fallback was at build time instead of the
# real gateway — this is exactly the bug that shipped: the runner stage set
# API_GATEWAY_URL=http://traefik, but the build here didn't, so every request
# silently rewrote to the http://localhost fallback, i.e. the frontend
# container itself, which has nothing listening on :80 (ECONNREFUSED).
ENV API_GATEWAY_URL=http://traefik
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# The gateway is reachable by service name inside the compose network.
ENV API_GATEWAY_URL=http://traefik

RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
USER nextjs

EXPOSE 3000
CMD ["npm", "run", "start"]
