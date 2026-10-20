ARG BUILD_FROM=ghcr.io/hassio-addons/base:16.3.3
FROM ${BUILD_FROM}

WORKDIR /app

# Upgrade base packages to avoid musl revision mismatch, then install python + dependencies
RUN apk update \
    && apk upgrade --no-cache \
    && apk add --no-cache \
        python3 \
        py3-pip \
        py3-psutil \
        gcc \
        musl-dev \
        linux-headers \
        python3-dev

COPY requirements.txt /app/
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app /app/app
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD [ "/run.sh" ]
