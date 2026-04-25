from __future__ import annotations

import ipaddress
import json
import sys
from dataclasses import asdict, dataclass
from typing import Optional

import dns.exception
import dns.resolver
import dns.reversename
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    help="Reverse-DNS (PTR) lookup for an IP address.",
)
console = Console()
err_console = Console(stderr=True)


@dataclass
class PtrResult:
    ip: str
    reverse_name: str
    resolver: str
    ptr_records: list[str]


def _validate_ip(s: str) -> str:
    try:
        return str(ipaddress.ip_address(s))
    except ValueError as e:
        raise RuntimeError(f"Not a valid IP address: {s!r}") from e


def lookup(ip: str, resolver: Optional[str], timeout: float) -> PtrResult:
    addr = _validate_ip(ip)
    rev_name = dns.reversename.from_address(addr)

    r = dns.resolver.Resolver(configure=resolver is None)
    if resolver:
        r.nameservers = [resolver]
    r.timeout = timeout
    r.lifetime = timeout

    used_resolver = resolver if resolver else (r.nameservers[0] if r.nameservers else "system")
    rev_name_str = str(rev_name).rstrip(".")

    try:
        answers = r.resolve(rev_name, "PTR")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return PtrResult(ip=addr, reverse_name=rev_name_str, resolver=used_resolver, ptr_records=[])
    except dns.exception.Timeout as e:
        raise RuntimeError(f"DNS query timed out after {timeout}s (resolver={used_resolver})") from e
    except dns.resolver.NoNameservers as e:
        raise RuntimeError(f"All nameservers failed for {rev_name_str} (resolver={used_resolver}): {e}") from e
    except dns.exception.DNSException as e:
        raise RuntimeError(f"DNS error: {e}") from e

    names = [str(a.target).rstrip(".") for a in answers]
    return PtrResult(ip=addr, reverse_name=rev_name_str, resolver=used_resolver, ptr_records=names)


def render_pretty(res: PtrResult) -> None:
    meta = Table(
        title=f"PTR Lookup — {res.ip}",
        title_style="bold cyan",
        show_header=False,
        expand=False,
        pad_edge=False,
    )
    meta.add_column("Field", style="bold magenta", no_wrap=True)
    meta.add_column("Value", overflow="fold")
    meta.add_row("IP", res.ip)
    meta.add_row("Reverse name", res.reverse_name)
    meta.add_row("Resolver", res.resolver)
    console.print(meta)

    if res.ptr_records:
        body = "\n".join(f"  • {n}" for n in res.ptr_records)
        console.print(Panel(body, title=f"FQDNs  ({len(res.ptr_records)})", title_align="left", border_style="green"))
    else:
        console.print(
            Panel(
                "  [dim]No PTR records found (NXDOMAIN / NoAnswer)[/]",
                title="FQDNs  (0)",
                title_align="left",
                border_style="yellow",
            )
        )


@app.command(no_args_is_help=True)
def main(
    ip: str = typer.Argument(..., metavar="IP", help="IP address (v4 or v6) to look up"),
    resolver: Optional[str] = typer.Option(
        None, "--resolver", "-r", help="DNS resolver to query (e.g. 1.1.1.1). Default: system resolver."
    ),
    timeout: float = typer.Option(5.0, "--timeout", "-t", help="DNS timeout in seconds"),
    output_json: bool = typer.Option(False, "--json", "-j", help="Emit JSON instead of pretty output"),
) -> None:
    """Perform a PTR (reverse-DNS) lookup on IP and report the FQDN(s)."""
    if not output_json:
        resolver_note = f" via {resolver}" if resolver else ""
        console.print(f"[dim]→ querying PTR for {ip}{resolver_note} ...[/]")

    try:
        result = lookup(ip, resolver, timeout)
    except RuntimeError as e:
        err_console.print(f"[bold red]error[/]: {e}")
        raise typer.Exit(code=2)

    if output_json:
        sys.stdout.write(json.dumps(asdict(result), indent=2, default=str))
        sys.stdout.write("\n")
    else:
        render_pretty(result)

    if not result.ptr_records:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
