FROM python:3.12-alpine

WORKDIR /app

# Install build dependencies if needed and clean up
RUN apk add --no-cache gcc musl-dev linux-headers

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV PORT_SCOUT_PORT=5055 \
    PORT_SCOUT_HOST=0.0.0.0 \
    DEFAULT_MIN_PORT=8000 \
    DEFAULT_MAX_PORT=9999

EXPOSE 5055

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:5055/api/v1/health || exit 1

CMD ["python", "-m", "app.main"]
