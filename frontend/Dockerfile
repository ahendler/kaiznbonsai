FROM node:20-alpine

WORKDIR /app

# Copy dependency definitions and install them
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "--host"]
