ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Setup base system
RUN apk add --no-cache \
    python3 \
    py3-pip \
    i2c-tools \
    bash

# Install Python packages
RUN pip3 install --no-cache-dir \
    smbus2 \
    luma.oled \
    Pillow \
    requests

# Copy data
COPY run.sh /
COPY argon_oled.py /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
