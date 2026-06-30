FROM node:20-alpine

WORKDIR /app

# Copy dependency definitions and install them (image layer cache)
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

CMD ["sh", "-c", "npm ci && npm run dev -- --host"]
