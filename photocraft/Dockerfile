FROM alpine:3.21 AS bundle
COPY photocraft-web-0.23.1.zip /tmp/photocraft.zip
RUN echo "3a498eb517bca6cec89f9c6b1fc6448269a05428c8a3a4637c16817da157f03c  /tmp/photocraft.zip" | sha256sum -c - \
    && mkdir -p /tmp/photo /site/licenses \
    && unzip -q /tmp/photocraft.zip -d /tmp/photo \
    && cp -a /tmp/photo/photocraft-web-0.23.1/. /site/ \
    && cp /site/LICENSE-MIT /site/NOTICE /site/ATTRIBUTION.md /site/licenses/

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=bundle /site/ /usr/share/nginx/html/
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD wget -q --spider http://127.0.0.1:8080/healthz || exit 1
