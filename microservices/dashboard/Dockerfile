# 
# ETAPA 1: BUILD (compilar React)
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar dependencias
COPY package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto del código
COPY . .

# Compilar React (genera la carpeta dist/)
RUN npm run build

# ETAPA 2: SERVIR CON NGINX
FROM nginx:alpine

# Copiar el build de React al directorio de Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar la configuración de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer el puerto 80
EXPOSE 80

# Comando de inicio
CMD ["nginx", "-g", "daemon off;"]