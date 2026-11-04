#!/bin/sh
# One update per invocation; scheduling belongs to the caller.
set -eu
set -f

DNS_PROVIDER=${DNS_PROVIDER:-duckdns}

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
require() {
    # Only variable names from the fixed provider dispatch reach eval.
    eval 'value=${'"$1"':-}'
    [ -n "$value" ] || die "$1 is required"
}

require_list() {
    require "$1"
    case "$value" in
        ,*|*,|*,,*|*[[:space:]]*) die "$1 must be a comma-separated list without empty entries or whitespace" ;;
    esac
}

request() {
    # Do not print curl stderr, request URLs, provider bodies or credentials.
    # No automatic retries: the scheduler controls retries and provider limits.
    RESPONSE=$(curl --silent --fail --proto '=https' --connect-timeout 10 \
        --max-time 30 --max-filesize 65536 --write-out '\n%{http_code}' "$@" 2>/dev/null) \
        || die "DNS request failed (transport, timeout or HTTP error)"
    newline='
'
    HTTP_STATUS=${RESPONSE##*"$newline"}
    RESPONSE=${RESPONSE%"$newline"*}
    # Providers may terminate their response with CRLF. Command substitution
    # removes trailing newlines; omit carriage returns before classification.
    RESPONSE=$(printf '%s' "$RESPONSE" | tr -d '\r')
    [ "$HTTP_STATUS" = 200 ] || die "DNS provider returned an unsuccessful HTTP status"
}

accept_dyndns() {
    case "$RESPONSE" in
        good|good\ *|nochg|nochg\ *) log "DNS update accepted" ;;
        badauth) die "DNS provider rejected authentication" ;;
        nohost) die "DNS provider rejected the hostname" ;;
        abuse) die "DNS provider blocked updates" ;;
        911|dnserr) die "DNS provider temporarily unavailable; retry later" ;;
        *) die "DNS provider returned an unexpected response" ;;
    esac
}

case "$DNS_PROVIDER" in
    duckdns)
        require DUCKDNS_TOKEN
        require_list DUCKDNS_DOMAINS
        request --ipv4 --get 'https://www.duckdns.org/update' \
            --data-urlencode "domains=$DUCKDNS_DOMAINS" \
            --data-urlencode "token=$DUCKDNS_TOKEN" --data-urlencode 'ip='
        [ "$RESPONSE" = OK ] || die "DuckDNS rejected the update"
        log "DNS update accepted"
        ;;
    freedns)
        require_list FREEDNS_TOKEN
        previous_ifs=$IFS
        IFS=,
        for token in $FREEDNS_TOKEN; do
            request "https://sync.afraid.org/u/$token/"
            case "$RESPONSE" in
                Updated*|*'has not changed'*) log "DNS update accepted" ;;
                *) die "FreeDNS rejected the update or returned an unexpected response" ;;
            esac
        done
        IFS=$previous_ifs
        ;;
    dynu)
        require DYNU_PASSWORD
        if [ -n "${DYNU_HOSTNAME:-}" ]; then
            [ -z "${DYNU_GROUP:-}" ] || die "Set DYNU_HOSTNAME or DYNU_GROUP, not both"
            selector="hostname=$DYNU_HOSTNAME"
        else
            require DYNU_GROUP
            selector="group=$DYNU_GROUP"
        fi
        request --ipv4 --get 'https://api.dynu.com/nic/update' \
            --data-urlencode "$selector" --data-urlencode 'myip=' \
            --data-urlencode "password=$DYNU_PASSWORD"
        accept_dyndns
        ;;
    desec)
        require DESEC_TOKEN
        require_list DESEC_DOMAINS
        # Default to IPv4 discovery while preserving existing AAAA records.
        # Explicit empty values can delete records, so reject them.
        ipv4=${DESEC_IPV4-auto}
        ipv6=${DESEC_IPV6-preserve}
        if [ -z "$ipv4" ] || [ -z "$ipv6" ]; then
            die "DESEC_IPV4 and DESEC_IPV6 must not be empty"
        fi
        set -- --get 'https://update.dedyn.io/' \
            --header "Authorization: Token $DESEC_TOKEN" \
            --data-urlencode "hostname=$DESEC_DOMAINS"
        if [ "$ipv4" = auto ]; then
            [ "$ipv6" != auto ] || die "Only one deSEC address family may use auto"
            set -- "$@" --ipv4
        else
            set -- "$@" --data-urlencode "myipv4=$ipv4"
        fi
        if [ "$ipv6" = auto ]; then
            set -- "$@" --ipv6
        else
            set -- "$@" --data-urlencode "myipv6=$ipv6"
        fi
        request "$@"
        accept_dyndns
        ;;
    *) die "Unknown DNS_PROVIDER" ;;
esac
