FROM python:3.11-slim-bullseye
RUN mkdir /bot && chmod 777 /bot
WORKDIR /bot
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt install -y --no-install-recommends git wget pv jq python3-dev ffmpeg mediainfo build-essential && rm -rf /var/lib/apt/lists/*
RUN apt-get install neofetch wget -y -f

COPY . .
RUN pip3 install -r requirements.txt
CMD ["bash","run.sh"]
