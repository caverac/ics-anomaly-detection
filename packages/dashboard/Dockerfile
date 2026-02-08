# Build stage
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build

# Production stage - serve with nginx
FROM nginx:alpine

# Copy built files to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Configure nginx for SPA routing
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location /api { \
        proxy_pass http://alerting:8084; \
        proxy_http_version 1.1; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
