FROM node:20-alpine
WORKDIR /app
COPY package.json tsconfig.json next.config.mjs next-env.d.ts ./
RUN npm install
COPY app ./app
COPY lib ./lib
RUN npm run build
EXPOSE 3000
