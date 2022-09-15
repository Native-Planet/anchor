# Build Caddy from master until 2.6 release
FROM golang:1.19.1-alpine3.16 as builder
WORKDIR /
RUN apk add --no-cache git
RUN git clone https://github.com/caddyserver/caddy.git
WORKDIR /caddy/cmd/caddy/
RUN go build

FROM caddy:2-alpine
WORKDIR /
RUN rm /usr/bin/caddy
COPY --from=builder /caddy/cmd/caddy/caddy /usr/bin/caddy
RUN chmod +x /usr/bin/caddy
RUN apk add --no-cache libcap curl
RUN setcap 'cap_net_bind_service=+ep' /usr/bin/caddy
COPY ./default_config.json /etc/caddy/
RUN echo "#!/bin/ash" > /init
RUN echo "ip route add 10.13.13.0/24 via 172.20.0.2" >> /init
RUN echo "exec caddy run --config /etc/caddy/default_config.json --resume" >> /init
RUN chmod +x /init
EXPOSE 80
EXPOSE 443
CMD ["ash", "/init"]