FROM alpine:3.24.3@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a

LABEL org.opencontainers.image.title="Dynamic DNS Updater" \
      org.opencontainers.image.description="One-shot updater for DuckDNS, FreeDNS, Dynu and deSEC" \
      org.opencontainers.image.licenses="MIT"

RUN apk --no-cache add curl ca-certificates
COPY --chmod=0755 update_dns.sh /usr/local/bin/update_dns.sh
COPY LICENSE /usr/share/licenses/dynamic-dns-updater/LICENSE
USER 65532:65532
WORKDIR /tmp
CMD ["/usr/local/bin/update_dns.sh"]
