ARG BUILD_FROM=ghcr.io/hassio-addons/base:16.3.3
FROM ${BUILD_FROM}

WORKDIR /app

# Install python3, pip, and precompiled py3-psutil from Alpine repo (zero C-compilation)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-psutil

COPY requirements.txt /app/
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app /app/app
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD [ "/run.sh" ]
