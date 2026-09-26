# Sourced by the image's /usr/bin/chromium wrapper (Debian: every file in /etc/chromium.d/ is
# sourced before exec). Opens Chrome's DevTools port INSIDE the container (127.0.0.1:9222 only —
# headed Chrome ignores --remote-debugging-address). The `cdp` sidecar in docker-compose.yml
# shares this network namespace and forwards 9223 -> 127.0.0.1:9222, published to the host as
# 127.0.0.1:9223, so our workers drive the same logged-in browser the CEO used from his phone.
# Not a stock neko feature (m1k1o/neko issue #391) — this file is the whole override.
export CHROMIUM_FLAGS="$CHROMIUM_FLAGS --remote-debugging-port=9222"
