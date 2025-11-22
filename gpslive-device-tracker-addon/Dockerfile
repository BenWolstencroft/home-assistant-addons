ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Setup base system
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash

# Copy requirements file
COPY requirements.txt /tmp/

# Install Python packages
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# Copy data
COPY run.sh /
COPY gpslive_tracker.py /

RUN chmod a+x /run.sh
RUN chmod a+x /gpslive_tracker.py

CMD [ "/run.sh" ]
