# Separated Silverman Authority Manager UI (US-093 / BL-034 Story 1).
# Multi-stage: Node builds Vite SPA (base /) → nginx serves static assets.
# Runtime injects non-secret config.js from SILVERMAN_OPERATOR_UI_API_BASE_URL.

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY src ./src
ENV VITE_OPERATOR_UI_DELIVERY=separated
RUN npm run build

FROM nginx:1.27-alpine
# gettext provides envsubst for US-099 private-hop upstream injection.
RUN apk add --no-cache gettext
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
    && printf '%s\n' \
      'window.__SILVERMAN_OPERATOR_UI_CONFIG__ = {"deliveryMode":"separated","apiBaseUrl":"","envLabel":""};' \
      > /usr/share/nginx/html/config.js

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
