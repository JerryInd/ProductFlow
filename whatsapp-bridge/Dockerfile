FROM node:20-slim

RUN apt-get update -qq && apt-get install -y -qq git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

CMD ["node", "bridge.js"]
