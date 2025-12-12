FROM node:20-alpine

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm install

# 复制代码
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
