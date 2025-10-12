FROM python:3.11-slim-bullseye
RUN mkdir /bot && chmod 777 /bot
WORKDIR /bot
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update -y && DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends git wget pv jq python3-dev ffmpeg mediainfo build-essential neofetch && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools wheel

COPY . .
RUN pip3 install -r requirements.txt
CMD ["bash","run.sh"]
