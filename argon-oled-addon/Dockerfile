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
    gcc \
    musl-dev \
    python3-dev \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev

# Install Python packages
# Install luma.core with system Pillow, then luma.oled will use it
RUN pip3 install --no-cache-dir \
    smbus2 \
    requests \
    cbor2 \
    luma.core==2.4.2 --no-deps

# Install luma.oled without dependencies (to avoid Pillow reinstall)
RUN pip3 install --no-cache-dir luma.oled --no-deps

# Copy data
COPY run.sh /
COPY argon_oled.py /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
