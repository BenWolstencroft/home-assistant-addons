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
    py3-pillow \
    libgpiod \
    py3-libgpiod

# Copy requirements file
COPY requirements.txt /tmp/

# Install Python packages
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Install luma packages using system Pillow (no-deps to avoid Pillow reinstall)
RUN pip3 install --no-cache-dir --no-deps luma.core luma.oled

# Copy data
COPY run.sh /
COPY argon_oled.py /
COPY system_info.py /
COPY supervisor_api.py /
COPY screens.py /
COPY logo.png /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
