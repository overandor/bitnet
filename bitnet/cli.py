"""CLI — bitnet watch, bitnet demo, bitnet verify."""

import asyncio
import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from bitnet.db import init_db, get_db
from bitnet.scanner import FolderSnapshot
from bitnet.merkle import verify_merkle_proof
from bitnet.watcher import upsert_watcher, stop_watcher, record_run
from bitnet.anchor import anchor_service
from bitnet.receipt import make_receipt, receipt_hash, verify_receipt
from bitnet.proof import export_proof, verify_proof_bundle, replay_snapshot

console = Console()

DEMO_FOLDER = Path(__file__).parent.parent / "demo" / "sample-folder"


def print_banner():
    banner = Text()
    banner.append("BitNet", style="bold bright_cyan")
    banner.append(" — Self-Proving Folders", style="dim")
    console.print(Panel(banner, border_style="cyan"))


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """BitNet — Continuous cryptographic provenance for your filesystem."""
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print("\n[dim]Commands:[/dim]")
        console.print("  [cyan]bitnet demo[/cyan]        Run a zero-setup demo")
        console.print("  [cyan]bitnet watch <path>[/cyan]  Start watching a folder")
        console.print("  [cyan]bitnet verify[/cyan]      Verify a snapshot receipt")
        console.print("  [cyan]bitnet export-proof[/cyan]  Export a portable proof bundle")
        console.print("  [cyan]bitnet verify-proof[/cyan]  Verify a proof bundle")
        console.print("  [cyan]bitnet replay[/cyan]      Rescan and compare against a receipt")
        console.print("  [cyan]bitnet serve[/cyan]       Launch the web dashboard")
        console.print("\n[dim]More: https://github.com/bitnet/bitnet[/dim]\n")


@main.command()
def demo():
    """Run a zero-setup demo with synthetic files."""
    print_banner()
    console.print("\n[bold]Demo[/bold]: Scanning synthetic sample folder...\n")

    demo_path = DEMO_FOLDER
    if not demo_path.exists():
        _create_demo_files(demo_path)

    snapshot = FolderSnapshot(demo_path, max_files=50).scan()

    table = Table(title="BitNet Demo Scan Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Folder", str(snapshot.root))
    table.add_row("Files Scanned", str(len(snapshot.files)))
    table.add_row("Duplicate Groups", str(snapshot.duplicate_groups))
    table.add_row("Duplicate Files", str(snapshot.duplicate_files))
    table.add_row("Total Bytes", f"{snapshot.total_bytes:,}")
    table.add_row("Merkle Root", snapshot.merkle_root)

    console.print(table)

    # Demonstrate proof
    if snapshot.files:
        target = snapshot.files[0]
        from bitnet.merkle import generate_merkle_proof
        proof = generate_merkle_proof(target["raw_hash"], [f["raw_hash"] for f in snapshot.files])
        valid = verify_merkle_proof(snapshot.merkle_root, proof, target["raw_hash"])
        console.print(f"\n[dim]Merkle proof for {target['rel_path']}:[/dim]")
        console.print(f"  Valid: [{'green' if valid else 'red'}]{valid}[/]")
        console.print(f"  Proof depth: {len(proof)} sibling hashes")

    # Canonical receipt
    receipt = make_receipt(snapshot)
    console.print(f"\n[dim]Receipt (hash {receipt_hash(receipt)[:16]}...):[/dim]")
    console.print(json.dumps(receipt, indent=2, sort_keys=True))
    console.print("\n[green]Demo complete.[/green] Try: [cyan]bitnet watch <your-folder>[/cyan]\n")


def _create_demo_files(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    (path / "src").mkdir(exist_ok=True)
    (path / "src" / "main.py").write_text("# Main entry point\ndef main():\n    print('hello')\n")
    (path / "src" / "utils.py").write_text("# Utilities\ndef helper():\n    pass\n")
    (path / "config.json").write_text('{"version": "1.0.0", "debug": false}\n')
    (path / "README.md").write_text("# Sample Project\n\nA demo folder for BitNet.\n")
    (path / "data.csv").write_text("id,name,value\n1,alpha,100\n2,beta,200\n")
    # Create a duplicate
    (path / "backup").mkdir(exist_ok=True)
    (path / "backup" / "README.md").write_text("# Sample Project\n\nA demo folder for BitNet.\n")


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--max-files", default=250, help="Maximum files to scan")
@click.option("--continuous", is_flag=True, help="Start a continuous watcher")
@click.option("--anchor", is_flag=True, help="Anchor Merkle root to Solana (requires key)")
@click.option("--output", "output_path", type=click.Path(), help="Write receipt JSON to file")
def watch(folder: str, max_files: int, continuous: bool, anchor: bool, output_path: str):
    """Scan and optionally watch a folder for changes."""
    print_banner()
    folder_path = Path(folder).resolve()
    console.print(f"\n[bold]Scanning:[/bold] {folder_path}\n")

    asyncio.run(init_db())

    snapshot = FolderSnapshot(folder_path, max_files).scan()

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Files", str(len(snapshot.files)))
    table.add_row("Duplicates", str(snapshot.duplicate_files))
    table.add_row("Total Bytes", f"{snapshot.total_bytes:,}")
    table.add_row("Merkle Root", snapshot.merkle_root[:64] + "...")
    console.print(table)

    # Persist
    db = asyncio.run(get_db())
    try:
        run_id = asyncio.run(record_run(db, str(folder_path), snapshot))
    finally:
        asyncio.run(db.close())

    console.print(f"\n[dim]Saved as run_id={run_id}[/dim]")

    # Write canonical receipt to file if requested
    if output_path:
        receipt = make_receipt(snapshot)
        Path(output_path).write_text(json.dumps(receipt, indent=2, sort_keys=True))
        console.print(f"[dim]Canonical receipt written to {output_path}[/dim]")

    # Optional anchor
    if anchor:
        if not anchor_service.available:
            console.print("[yellow]Solana anchoring not available. Set SOLANA_KEYPAIR_PATH.[/yellow]")
        else:
            result = asyncio.run(anchor_service.anchor_folder(str(folder_path), snapshot.merkle_root, len(snapshot.files)))
            if result and result.get("status") == "confirmed":
                console.print(f"[green]Anchored:[/green] {result['explorer_url']}")
            else:
                console.print(f"[red]Anchor failed:[/red] {result}")

    if continuous:
        watcher = asyncio.run(upsert_watcher(str(folder_path), max_files=max_files, anchor=anchor))
        console.print(f"\n[green]Watcher started[/green] (id={watcher['id']}, interval=300s)")
        console.print("[dim]Press Ctrl+C to stop.[/dim]")
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            asyncio.run(stop_watcher(watcher["id"]))
            console.print("\n[dim]Watcher stopped.[/dim]")


@main.command()
@click.argument("receipt_json", type=str)
def verify(receipt_json: str):
    """Verify a snapshot receipt format and integrity."""
    print_banner()
    try:
        receipt = json.loads(receipt_json)
    except Exception:
        console.print("[red]Invalid JSON receipt.[/red]")
        return

    report = verify_receipt(receipt)
    console.print(f"\n[bold]Verifying Receipt[/bold]\n")
    console.print(f"  Schema: {receipt.get('schema', 'unknown')}")
    console.print(f"  Root: {receipt.get('root')}")
    console.print(f"  Merkle Root: {receipt.get('merkle_root')}")
    console.print(f"  Files: {receipt.get('files_seen')}")
    console.print(f"  Hash: {report['receipt_hash'][:32]}...")
    if report["valid"]:
        console.print(f"\n[green]Receipt format valid and canonical.[/green]")
    else:
        console.print(f"\n[red]Receipt invalid:[/red] {'; '.join(report['errors'])}")
    console.print("[dim]To verify file integrity, re-scan the folder and compare Merkle roots.[/dim]\n")


@main.command("export-proof")
@click.argument("folder", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument("output", type=click.Path())
@click.option("--max-files", default=250, help="Maximum files to scan")
def export_proof_cmd(folder: str, output: str, max_files: int):
    """Export a portable proof bundle for a folder."""
    print_banner()
    folder_path = Path(folder).resolve()
    console.print(f"\n[bold]Exporting proof:[/bold] {folder_path}\n")

    snapshot = FolderSnapshot(folder_path, max_files).scan()
    out_path = export_proof(snapshot, Path(output))

    console.print(f"[green]Proof bundle written:[/green] {out_path}")
    console.print(f"  Files: {len(snapshot.files)}")
    console.print(f"  Merkle Root: {snapshot.merkle_root[:64]}...")
    console.print(f"\n[dim]Share this file. Anyone can verify it with:[/dim]")
    console.print(f"  [cyan]bitnet verify-proof {out_path}[/cyan]\n")


@main.command("verify-proof")
@click.argument("bundle_path", type=click.Path(exists=True, dir_okay=False))
def verify_proof_cmd(bundle_path: str):
    """Verify a portable proof bundle independently."""
    print_banner()
    path = Path(bundle_path)
    console.print(f"\n[bold]Verifying proof bundle:[/bold] {path}\n")

    report = verify_proof_bundle(path)
    table = Table()
    table.add_column("Check", style="cyan")
    table.add_column("Result", style="green")
    table.add_row("Receipt valid", str(report["receipt_valid"]))
    table.add_row("Merkle root match", str(report["merkle_root_match"]))
    table.add_row("Files verified", f"{report['files_verified']} / {report['files_total']}")
    console.print(table)

    if report["valid"]:
        console.print("\n[green]Proof bundle is valid and independently verifiable.[/green]\n")
    else:
        console.print(f"\n[red]Proof bundle invalid:[/red] {'; '.join(report['errors'])}\n")


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument("receipt_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--max-files", default=250, help="Maximum files to scan")
def replay(folder: str, receipt_path: str, max_files: int):
    """Rescan a folder and compare against a previous receipt."""
    print_banner()
    folder_path = Path(folder).resolve()
    console.print(f"\n[bold]Replaying snapshot:[/bold] {folder_path}\n")

    try:
        previous = json.loads(Path(receipt_path).read_text())
    except Exception as exc:
        console.print(f"[red]Cannot read receipt:[/red] {exc}")
        return

    report = replay_snapshot(folder_path, previous, max_files)

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Status", report["status"].upper())
    table.add_row("Previous Merkle Root", report["previous_merkle_root"][:64] + "...")
    table.add_row("Current Merkle Root", report["current_merkle_root"][:64] + "...")
    table.add_row("Previous Files", str(report["previous_files_seen"]))
    table.add_row("Current Files", str(report["files_seen"]))
    console.print(table)

    if report["match"]:
        console.print("\n[green]Folder is unchanged. Receipt verified.[/green]\n")
    elif report["status"] == "tampered":
        console.print("\n[red]Folder has changed. Tampering detected.[/red]")
        console.print("[dim]Merkle roots do not match.[/dim]\n")
    else:
        console.print(f"\n[red]Error:[/red] {'; '.join(report['errors'])}\n")


@main.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8765, type=int)
def serve(host: str, port: int):
    """Launch the web dashboard."""
    print_banner()
    console.print(f"\n[green]Dashboard running at http://{host}:{port}[/green]\n")
    from bitnet.web import run_server
    run_server()


if __name__ == "__main__":
    main()
