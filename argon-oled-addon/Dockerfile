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

# Install Python packages
RUN pip3 install --no-cache-dir \
    smbus2 \
    requests \
    cbor2 \
    qrcode

# Note: RPi.GPIO is not installed due to compilation issues with musl in the base image.
# The button functionality will be disabled, but all display features will work.

# Install luma packages using system Pillow
RUN pip3 install --no-cache-dir --no-deps luma.core luma.oled

# Copy data
COPY run.sh /
COPY argon_oled.py /
COPY logo.png /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
