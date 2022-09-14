# NP endpoint node API
FROM python:3.9-slim-buster as node-api

ENV PYTHONUNBUFFERED="true" \
    PYTHONIOENCODING=UTF-8 \
    PYTHONHASHSEED=0

RUN echo "deb http://deb.debian.org/debian buster-backports main non-free" >> /etc/apt/sources.list
RUN apt-get update && apt-get --no-install-recommends install -y curl wget vim python3-pip procps apt-utils wireguard wireguard-tools
COPY ./ /app
RUN pip3 install -r /app/requirements.txt

EXPOSE 8090
ENTRYPOINT ["python3","/app/app.py","-e","prod"]