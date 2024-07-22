# FROM balenalib/rpi-raspbian:bookworm
FROM arm64v8/debian:latest

ENV HOME=/root \
	DEBIAN_FRONTEND=noninteractive \
	LANG=en_US.UTF-8 \
	LANGUAGE=en_US.UTF-8 \
	LC_ALL=C.UTF-8 \
    SERIAL_0=00050869 \
    SERIAL_1=00050591

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
    tzdata software-properties-common \
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

COPY /Code /root/code
#COPY /Data /root/data

EXPOSE 9001

# Run Scripts via supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]


