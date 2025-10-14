FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install && npm cache clean --force

FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app/.next/standalone ./standalone
COPY --from=build /app/.next/static ./standalone/.next/static
COPY --from=build /app/public ./standalone/public
COPY package.json ./standalone/package.json
WORKDIR /app/standalone
EXPOSE 3000
CMD ["node", "server.js"]
