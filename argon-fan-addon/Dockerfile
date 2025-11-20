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

# Install Python packages for I2C communication
RUN pip3 install --no-cache-dir \
    smbus2

# Copy data
COPY run.sh /
COPY argon_fan.py /

RUN chmod a+x /run.sh
RUN chmod a+x /argon_fan.py

CMD [ "/run.sh" ]
