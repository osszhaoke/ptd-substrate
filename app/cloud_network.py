"""Choose a verified TLS route before authentication in single-process workers.

System DNS (including VPN DNS) is preferred. The existing public DNS fallback
is only used if the system path fails. No OS routing, trust, or VPN mutations.
Never use this getaddrinfo scope inside the multithreaded product server.
"""
from contextlib import contextmanager
import ipaddress
import json
import socket
import ssl
import urllib.request
import urllib.parse


def public_addresses(payload):
    if payload.get('Status') != 0:
        raise OSError('CN_DNS_FAILED')
    result = []
    for row in payload.get('Answer', []):
        if row.get('type') != 1:
            continue
        ip = ipaddress.ip_address(row['data'])
        if ip.version != 4 or not ip.is_global:
            raise OSError('CN_DNS_NONPUBLIC_ADDRESS')
        result.append(str(ip))
    if not result:
        raise OSError('CN_DNS_NO_ADDRESS')
    return result


def resolve_public(host):
    query = urllib.parse.urlencode({'name': host, 'type': 'A'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('https://dns.alidns.com/resolve?' + query, timeout=8) as response:
        return public_addresses(json.load(response))


def tls_ready(host):
    try:
        with socket.create_connection((host, 443), timeout=5) as raw:
            with ssl.create_default_context().wrap_socket(raw, server_hostname=host):
                return True
    except ssl.SSLCertVerificationError:
        raise  # Certificate errors are not bypassed by changing routes.
    except OSError:
        return False


@contextmanager
def cloud_route(hosts, primary):
    if primary not in hosts:
        raise ValueError('HOST_NOT_ALLOWED')
    if tls_ready(primary):
        yield 'system'
        return
    original = socket.getaddrinfo
    cache = {}
    def resolve(host, port, family=0, type=0, proto=0, flags=0):
        if host not in hosts:
            return original(host, port, family, type, proto, flags)
        if host not in cache:
            cache[host] = resolve_public(host)
        return [entry for ip in cache[host]
                for entry in original(ip, port, socket.AF_INET, type, proto, flags)]
    socket.getaddrinfo = resolve
    try:
        if not tls_ready(primary):
            raise OSError('CLOUD_ROUTE_UNREACHABLE')
        yield 'public_dns'
    finally:
        socket.getaddrinfo = original
