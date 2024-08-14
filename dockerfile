# TODO Set up environment variables in a way that I can automatically add new sensors to  supervisord config purely through environment variables like how mornedhels/enshrouded-server does it
FROM arm64v8/debian:latest

ENV HOME=/root \
	DEBIAN_FRONTEND=noninteractive \
	LANG=en_US.UTF-8 \
	LANGUAGE=en_US.UTF-8 \
	LC_ALL=C.UTF-8 \
    #SERIAL_0=00042412 \
    SERIAL_0=00050427 \
    SERIAL_1=00050420 \
    I2C_0=0x69 \
    I2C_1=0x68 \
    SUPERVISORD_PORT=9000 \
    MJPEG_PORT_0=8000 \
    MJPEG_PORT_1=8001

# Install base packages
RUN apt-get update

RUN apt-get install -y \
    build-essential \
    curl \
    supervisor \
    bash


# Install Rust
RUN apt-get update

RUN curl https://sh.rustup.rs -sSf | bash -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

# Install Python 3.11 and required packages
RUN apt-get install -y \
    tzdata \
    software-properties-common \
    python3-launchpadlib

RUN add-apt-repository 'ppa:deadsnakes/ppa'
RUN apt-get update
RUN apt-get install -y \
    python3.11 \
    python3-pip

COPY /Config/requirements.txt /root/requirements.txt
RUN pip install --break-system-packages -r /root/requirements.txt

RUN echo "deb http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list \
  && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 82B129927FA3303E

RUN apt update && apt install -y --no-install-recommends \
    python3-picamera2

# Config Set up

COPY /Config/65-neuromorphic-drivers.rules /etc/udev/rules.d/65-neuromorphic-drivers.rules
COPY /Config/99-camera.rules /etc/udev/rules.d/99-camera.rules
COPY /Config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY /Config/cam0_config.json /root/config/cam0_config.json
COPY /Config/cam1_config.json /root/config/cam1_config.json

COPY /Code /root/code
#COPY /Data /root/data

EXPOSE ${SUPERVISORD_PORT}
EXPOSE ${MJPEG_PORT_0}
EXPOSE ${MJPEG_PORT_1}

# Run Scripts via supervisord
# Change this to a shell script or python script that modifies the supervisord.conf file with the environment variables to add sensor compatability
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
#CMD ["python3", "/root/code/test.py", "--recordings /root/data/evk4_horizon --route horizon --port 8000 ${SERIAL_0}"]

