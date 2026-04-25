from __future__ import annotations

import ipaddress
import json
import socket
import ssl
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

import typer
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtensionOID, NameOID
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    help="Connect to a host on TLS, fetch its certificate, and extract metadata + FQDNs.",
)
console = Console()
err_console = Console(stderr=True)

NAME_OID_MAP = {
    NameOID.COMMON_NAME: "CN",
    NameOID.COUNTRY_NAME: "C",
    NameOID.LOCALITY_NAME: "L",
    NameOID.STATE_OR_PROVINCE_NAME: "ST",
    NameOID.ORGANIZATION_NAME: "O",
    NameOID.ORGANIZATIONAL_UNIT_NAME: "OU",
    NameOID.EMAIL_ADDRESS: "emailAddress",
    NameOID.SERIAL_NUMBER: "serialNumber",
}


@dataclass
class CertInfo:
    target: str
    port: int
    sni: Optional[str]
    subject: dict
    issuer: dict
    serial_number: str
    version: str
    not_valid_before: str
    not_valid_after: str
    days_until_expiry: int
    signature_algorithm: str
    public_key_type: str
    public_key_size: Optional[int]
    fingerprint_sha1: str
    fingerprint_sha256: str
    san_dns_names: list[str]
    san_ip_addresses: list[str]
    fqdns: list[str]


def _is_ip(s: str) -> bool:
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def _name_to_dict(name: x509.Name) -> dict[str, str]:
    out: dict[str, str] = {}
    for attr in name:
        key = NAME_OID_MAP.get(attr.oid, attr.oid.dotted_string)
        value = attr.value if isinstance(attr.value, str) else attr.value.decode("utf-8", errors="replace")
        out[key] = value
    return out


def _format_dn(dn: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in dn.items()) if dn else "-"


def fetch_certificate(host: str, port: int, sni: Optional[str], timeout: float) -> tuple[bytes, str]:
    """Open TCP, do a TLS handshake (no verification), return DER cert + negotiated TLS version."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    if sni:
        server_hostname: Optional[str] = sni
    elif _is_ip(host):
        server_hostname = None
    else:
        server_hostname = host

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=server_hostname) as ssock:
                der = ssock.getpeercert(binary_form=True)
                tls_version = ssock.version() or "unknown"
                if der is None:
                    raise RuntimeError("Server did not present a certificate")
                return der, tls_version
    except socket.timeout as e:
        raise RuntimeError(f"Connection to {host}:{port} timed out after {timeout}s") from e
    except ConnectionRefusedError as e:
        raise RuntimeError(f"Connection refused on {host}:{port} (port appears closed)") from e
    except ssl.SSLError as e:
        raise RuntimeError(f"TLS handshake with {host}:{port} failed: {e}") from e
    except OSError as e:
        raise RuntimeError(f"Network error reaching {host}:{port}: {e}") from e


def parse_certificate(der: bytes, target: str, port: int, sni: Optional[str]) -> CertInfo:
    cert = x509.load_der_x509_certificate(der)

    dns_names: list[str] = []
    ip_addresses: list[str] = []
    try:
        san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
        dns_names = list(san_ext.get_values_for_type(x509.DNSName))
        ip_addresses = [str(ip) for ip in san_ext.get_values_for_type(x509.IPAddress)]
    except x509.ExtensionNotFound:
        pass

    subject = _name_to_dict(cert.subject)
    issuer = _name_to_dict(cert.issuer)

    fqdns: list[str] = list(dict.fromkeys(dns_names))
    cn = subject.get("CN")
    if cn and "." in cn and cn not in fqdns and not _is_ip(cn):
        fqdns.append(cn)

    pub = cert.public_key()
    pub_type = type(pub).__name__.removesuffix("PublicKey")
    pub_size = getattr(pub, "key_size", None)

    not_before = cert.not_valid_before_utc
    not_after = cert.not_valid_after_utc
    days_left = (not_after - datetime.now(timezone.utc)).days

    sig_oid = cert.signature_algorithm_oid
    sig_name = getattr(sig_oid, "_name", None) or sig_oid.dotted_string

    return CertInfo(
        target=target,
        port=port,
        sni=sni,
        subject=subject,
        issuer=issuer,
        serial_number=f"{cert.serial_number:x}",
        version=cert.version.name,
        not_valid_before=not_before.isoformat(),
        not_valid_after=not_after.isoformat(),
        days_until_expiry=days_left,
        signature_algorithm=sig_name,
        public_key_type=pub_type,
        public_key_size=pub_size,
        fingerprint_sha1=cert.fingerprint(hashes.SHA1()).hex(":"),
        fingerprint_sha256=cert.fingerprint(hashes.SHA256()).hex(":"),
        san_dns_names=dns_names,
        san_ip_addresses=ip_addresses,
        fqdns=fqdns,
    )


def render_pretty(info: CertInfo, tls_version: str) -> None:
    target_label = f"{info.target}:{info.port}"
    if info.sni:
        target_label += f"  (SNI: {info.sni})"

    meta = Table(
        title=f"TLS Certificate — {target_label}  [{tls_version}]",
        title_style="bold cyan",
        show_header=False,
        expand=False,
        pad_edge=False,
    )
    meta.add_column("Field", style="bold magenta", no_wrap=True)
    meta.add_column("Value", overflow="fold")

    meta.add_row("Subject CN", info.subject.get("CN", "-"))
    meta.add_row("Subject", _format_dn(info.subject))
    meta.add_row("Issuer", _format_dn(info.issuer))
    meta.add_row("Serial", info.serial_number)
    meta.add_row("Version", info.version)
    meta.add_row("Not Before", info.not_valid_before)

    if info.days_until_expiry > 30:
        expiry_color = "green"
    elif info.days_until_expiry > 0:
        expiry_color = "yellow"
    else:
        expiry_color = "red"
    meta.add_row(
        "Not After",
        f"[{expiry_color}]{info.not_valid_after}  ({info.days_until_expiry} days remaining)[/]",
    )

    meta.add_row("Signature", info.signature_algorithm)
    pub_label = info.public_key_type + (f" ({info.public_key_size} bit)" if info.public_key_size else "")
    meta.add_row("Public Key", pub_label)
    meta.add_row("SHA-256", info.fingerprint_sha256.lower())
    meta.add_row("SHA-1", info.fingerprint_sha1.lower())

    console.print(meta)

    if info.fqdns:
        body = "\n".join(f"  • {n}" for n in info.fqdns)
    else:
        body = "  [dim]No FQDNs found in certificate[/]"
    console.print(Panel(body, title=f"FQDNs  ({len(info.fqdns)})", title_align="left", border_style="green"))

    if info.san_ip_addresses:
        ip_body = "\n".join(f"  • {n}" for n in info.san_ip_addresses)
        console.print(
            Panel(
                ip_body,
                title=f"SAN IP Addresses  ({len(info.san_ip_addresses)})",
                title_align="left",
                border_style="blue",
            )
        )


@app.command(no_args_is_help=True)
def main(
    host: str = typer.Argument(..., metavar="IP", help="IP address (or hostname) of the target server"),
    port: int = typer.Option(443, "--port", "-p", help="TCP port to connect to"),
    sni: Optional[str] = typer.Option(
        None,
        "--sni",
        "-s",
        help="Override the SNI server name. Defaults to none for IP literals, the host for names.",
    ),
    timeout: float = typer.Option(5.0, "--timeout", "-t", help="Connection timeout in seconds"),
    output_json: bool = typer.Option(False, "--json", "-j", help="Emit JSON instead of pretty output"),
) -> None:
    """Connect to IP:PORT, fetch the TLS certificate, and report metadata + FQDNs."""
    if not output_json:
        target = f"{host}:{port}"
        sni_note = f" (SNI={sni})" if sni else ""
        console.print(f"[dim]→ connecting to {target}{sni_note} ...[/]")

    try:
        der, tls_version = fetch_certificate(host, port, sni, timeout)
    except RuntimeError as e:
        err_console.print(f"[bold red]error[/]: {e}")
        raise typer.Exit(code=2)

    info = parse_certificate(der, host, port, sni)

    if output_json:
        payload = asdict(info)
        payload["tls_version"] = tls_version
        sys.stdout.write(json.dumps(payload, indent=2, default=str))
        sys.stdout.write("\n")
    else:
        render_pretty(info, tls_version)


if __name__ == "__main__":
    app()
