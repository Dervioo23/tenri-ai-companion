"""Centralized IPv4 forcing for hosts that break over NAT64/IPv6 on Windows.

Some ISPs return a NAT64 address (64:ff9b::/96) for ElevenLabs and Microsoft
Edge-TTS, which then fails the TLS handshake on Windows. Instead of each service
monkeypatching ``socket.getaddrinfo`` independently (fragile, import-order
dependent), they all register their host substrings here so a single wrapper
handles every case (BUG-15).
"""

import logging
import socket

logger = logging.getLogger("AICompanion.Network")

# Captured once, before any patching, so the wrapper always falls back to the
# real resolver.
_orig_getaddrinfo = socket.getaddrinfo
_forced_hosts: set[str] = set()
_installed = False


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host and any(h in str(host) for h in _forced_hosts):
        try:
            results = _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
            if results:
                return results
        except Exception:
            pass
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


def force_ipv4_for_hosts(*host_substrings: str) -> None:
    """Force IPv4 resolution for hosts whose name contains any given substring.

    Idempotent: installs the wrapper once and accumulates host substrings, so
    multiple services can call it in any order without chaining patches.
    """
    global _installed
    _forced_hosts.update(h for h in host_substrings if h)
    if not _installed:
        socket.getaddrinfo = _patched_getaddrinfo
        _installed = True
    logger.debug("IPv4-forced getaddrinfo active for hosts: %s", sorted(_forced_hosts))
