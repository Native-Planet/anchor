# Use a pinned version of linuxserver/wireguard
FROM linuxserver/wireguard@sha256:04a29519a7fd8da03fb001fbf9ec4b7a08b1e3563010cbeebbb62d5823728e9f
# Add a custom webhook that allows an authenticated & whitelisted IP to restart the WG interface
RUN apt update && apt install webhook
COPY ./hooks.json /etc/webhook/hooks.json
COPY ./restart.sh /etc/webhook/restart.sh
RUN chmod +x /etc/webhook/restart.sh
RUN sed -i '36 i sed -i "s|HOOK_AUTH|\${HEADER_AUTH}|g" /etc/webhook/hooks.json' /init
RUN sed -i '37 i webhook -hooks /etc/webhook/hooks.json -verbose &' /init
# curl http://172.20.0.2:9000/hooks/restart-wg?token={hook_auth}
# Uses the same token as private API auth, only accepts calls from API IP
EXPOSE 51820
EXPOSE 9000
ENTRYPOINT ["/init"]
