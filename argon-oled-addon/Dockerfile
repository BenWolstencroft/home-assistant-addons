ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Setup base system and build dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    i2c-tools \
    bash \
    py3-pillow \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev

# Install Python packages
RUN pip3 install --no-cache-dir \
    smbus2 \
    luma.oled \
    requests

# Copy data
COPY run.sh /
COPY argon_oled.py /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
