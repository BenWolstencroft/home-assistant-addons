ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Setup base system
RUN apk add --no-cache \
    python3 \
    py3-pip \
    i2c-tools \
    bash \
    py3-pillow

# Upgrade musl to fix version conflict, then install build dependencies
RUN apk upgrade --no-cache musl \
 && apk add --no-cache --virtual .build-deps \
    python3-dev \
    gcc \
    musl-dev \
    linux-headers \
 && pip3 install --no-cache-dir RPi.GPIO \
 && apk del .build-deps

# Install remaining Python packages
RUN pip3 install --no-cache-dir \
    smbus2 \
    requests \
    cbor2 \
    qrcode

# Install luma packages using system Pillow
RUN pip3 install --no-cache-dir --no-deps luma.core luma.oled

# Copy data
COPY run.sh /
COPY argon_oled.py /
COPY logo.png /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
