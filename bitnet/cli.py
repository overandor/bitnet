"""CLI — bitnet watch, bitnet demo, bitnet verify."""

import asyncio
import json
import os
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
from bitnet.git import get_git_root, get_head_commit, get_head_message, install_hook, uninstall_hook
from bitnet.agent_receipt import (
    AgentChain,
    make_agent_receipt,
    agent_receipt_hash,
    verify_agent_receipt,
    is_material_action,
    MATERIAL_ACTIONS,
)
from bitnet.snapshot import export_snapshot, verify_snapshot

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
        console.print("  [cyan]bitnet prove-repo[/cyan]  Prove current Git repository state")
        console.print("  [cyan]bitnet install-hook[/cyan] Install pre-commit hook")
        console.print("  [cyan]bitnet scan <path>[/cyan]  Scan without persistence")
        console.print("  [cyan]bitnet receipt <path> <out>[/cyan] Generate receipt file")
        console.print("  [cyan]bitnet diff <a> <b>[/cyan] Compare two receipts")
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
@click.argument("receipt_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--folder", type=click.Path(exists=True, file_okay=False, dir_okay=True), help="Override folder to rescan")
@click.option("--max-files", default=250, help="Maximum files to scan")
def verify(receipt_path: str, folder: str, max_files: int):
    """Verify a receipt by rescanning the folder and comparing Merkle roots."""
    print_banner()
    receipt_file = Path(receipt_path)
    try:
        receipt = json.loads(receipt_file.read_text())
    except Exception:
        console.print("[red]Cannot read receipt file.[/red]\n")
        return

    format_report = verify_receipt(receipt)
    console.print(f"\n[bold]Verifying Receipt[/bold]\n")
    console.print(f"  Schema: {receipt.get('schema', 'unknown')}")
    console.print(f"  Stored Root: {receipt.get('root')}")
    console.print(f"  Stored Merkle: {receipt.get('merkle_root')}")
    console.print(f"  Stored Files: {receipt.get('files_seen')}")
    console.print(f"  Receipt Hash: {format_report['receipt_hash'][:32]}...")
    if not format_report["valid"]:
        console.print(f"\n[red]Receipt format invalid:[/red] {'; '.join(format_report['errors'])}")
        return
    console.print(f"\n[green]Receipt format valid.[/green]")

    # Rescan
    scan_root = folder or receipt.get("root", "")
    if not scan_root:
        console.print("[red]No folder specified and receipt has no root field.[/red]\n")
        return
    scan_path = Path(scan_root)
    if not scan_path.exists():
        console.print(f"[red]Folder not found:[/red] {scan_path}\n")
        return

    console.print(f"\n[dim]Rescanning {scan_path}...[/dim]")
    snapshot = FolderSnapshot(scan_path, max_files).scan()
    current_root = snapshot.merkle_root
    stored_root = receipt.get("merkle_root", "")

    table = Table()
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Current Merkle", current_root)
    table.add_row("Stored Merkle", stored_root)
    table.add_row("Current Files", str(len(snapshot.files)))
    table.add_row("Stored Files", str(receipt.get("files_seen", 0)))
    console.print(table)

    if current_root == stored_root:
        console.print(f"\n[green]Folder integrity verified.[/green] No tampering detected.\n")
    else:
        console.print(f"\n[red]TAMPERING DETECTED.[/red] Merkle root mismatch.")
        console.print(f"  Folder state has changed since receipt was generated.\n")


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


@main.command("prove-repo")
@click.option("--output", "output_path", type=click.Path(), help="Write receipt JSON to file")
@click.option("--quiet", is_flag=True, help="Suppress banner and table output")
def prove_repo(output_path: str, quiet: bool):
    """Scan the current Git repository and generate a receipt with commit info."""
    if not quiet:
        print_banner()

    root = get_git_root()
    if not root:
        console.print("[red]Not inside a Git repository.[/red]")
        raise click.Abort()

    commit = get_head_commit()
    message = get_head_message()

    if not quiet:
        console.print(f"\n[bold]Proving repository:[/bold] {root}")
        console.print(f"  HEAD: {commit[:12]}..." if commit else "  HEAD: unknown")
        console.print(f"  {message}\n" if message else "")

    snapshot = FolderSnapshot(root, max_files=1000).scan()

    if not quiet:
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Files", str(len(snapshot.files)))
        table.add_row("Duplicates", str(snapshot.duplicate_files))
        table.add_row("Total Bytes", f"{snapshot.total_bytes:,}")
        table.add_row("Merkle Root", snapshot.merkle_root[:64] + "...")
        console.print(table)

    receipt = make_receipt(snapshot)
    receipt["git_commit"] = commit
    receipt["git_message"] = message

    if output_path:
        Path(output_path).write_text(json.dumps(receipt, indent=2, sort_keys=True))
        if not quiet:
            console.print(f"\n[dim]Receipt written to {output_path}[/dim]")

    if not quiet:
        console.print(f"\n[green]Repository proven.[/green] Receipt hash: {receipt_hash(receipt)[:16]}...\n")


@main.command("install-hook")
def install_hook_cmd():
    """Install the BitNet pre-commit hook in the current Git repository."""
    print_banner()
    hook_path = install_hook()
    if hook_path:
        console.print(f"\n[green]Hook installed:[/green] {hook_path}\n")
    else:
        console.print("[red]Not inside a Git repository.[/red]\n")


@main.command("uninstall-hook")
def uninstall_hook_cmd():
    """Remove the BitNet pre-commit hook from the current Git repository."""
    print_banner()
    if uninstall_hook():
        console.print("\n[green]Hook removed.[/green]\n")
    else:
        console.print("[red]No hook to remove.[/red]\n")


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--max-files", default=250, help="Maximum files to scan")
@click.option("--output", "output_path", type=click.Path(), help="Write receipt JSON to file")
def scan(folder: str, max_files: int, output_path: str):
    """Scan a folder and optionally output a receipt (no persistence)."""
    print_banner()
    folder_path = Path(folder).resolve()
    console.print(f"\n[bold]Scanning:[/bold] {folder_path}\n")
    snapshot = FolderSnapshot(folder_path, max_files).scan()

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Files", str(len(snapshot.files)))
    table.add_row("Duplicates", str(snapshot.duplicate_files))
    table.add_row("Total Bytes", f"{snapshot.total_bytes:,}")
    table.add_row("Merkle Root", snapshot.merkle_root)
    console.print(table)

    if output_path:
        receipt = make_receipt(snapshot)
        Path(output_path).write_text(json.dumps(receipt, indent=2, sort_keys=True))
        console.print(f"\n[dim]Receipt written to {output_path}[/dim]")
    console.print()


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument("output", type=click.Path())
@click.option("--max-files", default=250, help="Maximum files to scan")
def receipt(folder: str, output: str, max_files: int):
    """Generate a canonical receipt for a folder and write it to a file."""
    print_banner()
    folder_path = Path(folder).resolve()
    console.print(f"\n[bold]Generating receipt:[/bold] {folder_path}\n")
    snapshot = FolderSnapshot(folder_path, max_files).scan()
    receipt = make_receipt(snapshot)
    Path(output).write_text(json.dumps(receipt, indent=2, sort_keys=True))
    console.print(f"[green]Receipt written:[/green] {output}")
    console.print(f"  Hash: {receipt_hash(receipt)[:32]}...")
    console.print(f"  Files: {receipt['files_seen']}")
    console.print(f"  Merkle Root: {receipt['merkle_root'][:64]}...\n")


@main.command()
@click.argument("receipt_a", type=click.Path(exists=True, dir_okay=False))
@click.argument("receipt_b", type=click.Path(exists=True, dir_okay=False))
def diff(receipt_a: str, receipt_b: str):
    """Compare two receipts and show differences."""
    print_banner()
    try:
        a = json.loads(Path(receipt_a).read_text())
        b = json.loads(Path(receipt_b).read_text())
    except Exception as exc:
        console.print(f"[red]Cannot read receipt:[/red] {exc}\n")
        return

    console.print(f"\n[bold]Comparing receipts[/bold]\n")
    table = Table()
    table.add_column("Field", style="cyan")
    table.add_column("Receipt A", style="green")
    table.add_column("Receipt B", style="yellow")
    table.add_column("Status", style="white")

    fields = ["schema", "root", "merkle_root", "files_seen", "total_bytes", "scanned_at"]
    for field in fields:
        va = str(a.get(field, "N/A"))
        vb = str(b.get(field, "N/A"))
        status = "[green]match[/]" if va == vb else "[red]diff[/]"
        table.add_row(field, va[:48], vb[:48], status)

    console.print(table)

    if a.get("merkle_root") == b.get("merkle_root"):
        console.print("\n[green]Merkle roots match. Receipts describe the same folder state.[/green]\n")
    else:
        console.print("\n[red]Merkle roots differ. Folder state has changed between scans.[/red]\n")


@main.command()
@click.argument("receipt_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--key", type=click.Path(), help="Path to signing key (Ed25519 PEM)")
def sign(receipt_path: str, key: str):
    """Sign a BitNet receipt with a local key."""
    print_banner()
    console.print(f"\n[bold]Sign Receipt[/bold]\n")
    console.print("  [yellow]Status:[/yellow] PLANNED")
    console.print("  This command will cryptographically sign a receipt using Ed25519.")
    console.print("  The signature will be embedded in the receipt as:")
    console.print("    { ... , \"signature\": \"base64...\", \"public_key\": \"...\" }")
    console.print("  Track progress: https://github.com/overandor/bitnet/issues\n")


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument("output", type=click.Path())
@click.option("--max-files", default=250, help="Maximum files to scan")
def sbom(folder: str, output: str, max_files: int):
    """Generate an SBOM-compatible provenance receipt for a folder."""
    print_banner()
    console.print(f"\n[bold]SBOM Provenance[/bold]\n")
    console.print("  [yellow]Status:[/yellow] PLANNED")
    console.print("  This command will generate a SPDX/CycloneDX-compatible provenance document")
    console.print("  that binds the folder's Merkle root to a software bill of materials.")
    console.print("  Track progress: https://github.com/overandor/bitnet/issues\n")


@main.command("export-oscal")
@click.argument("receipt_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("output", type=click.Path())
def export_oscal(receipt_path: str, output: str):
    """Export a BitNet receipt as OSCAL assessment evidence."""
    print_banner()
    console.print(f"\n[bold]Export OSCAL[/bold]\n")
    console.print("  [yellow]Status:[/yellow] PLANNED")
    console.print("  This command will convert a BitNet receipt into NIST OSCAL assessment results")
    console.print("  for inclusion in Authority to Operate (ATO) packages.")
    console.print("  Track progress: https://github.com/overandor/bitnet/issues\n")


@main.command()
@click.argument("receipt_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--rekor", is_flag=True, help="Publish attestation to Sigstore Rekor")
@click.option("--key", type=click.Path(), help="Path to signing key")
def attest(receipt_path: str, rekor: bool, key: str):
    """Attest a receipt's validity (cryptographic signing + optional transparency log)."""
    print_banner()
    console.print(f"\n[bold]Attest Receipt[/bold]\n")
    console.print("  [yellow]Status:[/yellow] PLANNED")
    console.print("  This command will:")
    console.print("    1. Verify the receipt format and Merkle root")
    console.print("    2. Sign the receipt with an Ed25519 key")
    console.print("    3. Optionally publish to Sigstore Rekor for transparency")
    console.print("  Track progress: https://github.com/overandor/bitnet/issues\n")


@main.command("agent-action")
@click.argument("action_type", type=str)
@click.option("--agent-id", default="bitnet-cli", help="Agent identifier")
@click.option("--workspace-hash", default="", help="SHA-256 of workspace state")
@click.option("--input-hash", default="", help="SHA-256 of inputs")
@click.option("--output-hash", default="", help="SHA-256 of outputs")
@click.option("--tool-used", default="", help="Tool or sub-system that performed the action")
@click.option("--files-touched", default="", help="Comma-separated list of files touched")
@click.option("--merkle-root", default="", help="Merkle root if a folder snapshot was involved")
@click.option("--metadata", default="", help="JSON string of extra metadata")
@click.option("--anchor", is_flag=True, help="Anchor the action hash on-chain (Solana memo)")
@click.option("--quiet", is_flag=True, help="Suppress banner and table output")
def agent_action(
    action_type: str,
    agent_id: str,
    workspace_hash: str,
    input_hash: str,
    output_hash: str,
    tool_used: str,
    files_touched: str,
    merkle_root: str,
    metadata: str,
    anchor: bool,
    quiet: bool,
):
    """Log a material agent action to the receipt chain."""
    if not quiet:
        print_banner()

    if not is_material_action(action_type):
        if not quiet:
            console.print(f"\n[yellow]Skipped:[/yellow] '{action_type}' is not a material action under default policy.\n")
        return

    chain = AgentChain()
    files_list = [f.strip() for f in files_touched.split(",") if f.strip()] if files_touched else []
    meta = json.loads(metadata) if metadata else None

    entry = chain.append(
        action_type=action_type,
        agent_id=agent_id,
        workspace_hash=workspace_hash,
        input_hash=input_hash,
        output_hash=output_hash,
        tool_used=tool_used,
        files_touched=files_list,
        merkle_root=merkle_root,
        metadata=meta,
    )

    receipt = entry["receipt"]
    chain_hash = entry["chain_hash"]

    if not quiet:
        console.print(f"\n[bold]Agent Action Logged[/bold]\n")
        table = Table()
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Action ID", receipt["action_id"])
        table.add_row("Type", receipt["action_type"])
        table.add_row("Agent", receipt["agent_id"])
        table.add_row("Timestamp", receipt["timestamp"])
        table.add_row("Chain Hash", chain_hash[:32] + "...")
        if receipt["previous_action_hash"]:
            table.add_row("Previous Hash", receipt["previous_action_hash"][:32] + "...")
        else:
            table.add_row("Previous Hash", "(genesis)")
        console.print(table)

    if anchor:
        if not quiet:
            console.print(f"\n[dim]Anchoring to Solana...[/dim]")
        import asyncio
        memo = f"BITNET_ACTION:{chain_hash}"
        result = asyncio.run(anchor_service._send_memo(memo))
        if result and result.get("status") == "confirmed":
            entry["anchored"] = True
            if not quiet:
                console.print(f"[green]Anchored:[/green] {result['explorer_url']}")
        else:
            if not quiet:
                console.print(f"[red]Anchor failed:[/red] {result}")

    if not quiet:
        console.print()


@main.command("agent-chain-verify")
@click.option("--chain-path", type=click.Path(), help="Path to agent chain JSONL file")
@click.option("--quiet", is_flag=True, help="Output only result")
def agent_chain_verify(chain_path: str, quiet: bool):
    """Verify the integrity of the agent action hash chain."""
    if not quiet:
        print_banner()

    chain = AgentChain(Path(chain_path) if chain_path else None)
    report = chain.verify_chain()

    if quiet:
        print("VALID" if report["valid"] else "INVALID")
        if report["errors"]:
            for e in report["errors"]:
                print(f"ERROR: {e}")
        return

    console.print(f"\n[bold]Agent Chain Verification[/bold]\n")
    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Valid", str(report["valid"]))
    table.add_row("Entries", str(report["length"]))
    table.add_row("Errors", str(len(report["errors"])))
    console.print(table)

    if report["errors"]:
        console.print("\n[red]Errors:[/red]")
        for e in report["errors"]:
            console.print(f"  - {e}")
    else:
        console.print("\n[green]Chain integrity verified. No tampering detected.[/green]")
    console.print()


@main.command("agent-policy")
def agent_policy():
    """Show the default agent action anchoring policy."""
    print_banner()
    console.print("\n[bold]Agent Action Policy[/bold]\n")
    console.print("[cyan]Material actions (anchored by default):[/cyan]")
    for action in sorted(MATERIAL_ACTIONS):
        console.print(f"  [green]•[/green] {action}")
    console.print("\n[dim]All other actions are silently skipped.[/dim]\n")


@main.command("snapshot")
@click.argument("folder", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument("output_dir", type=click.Path())
@click.option("--max-files", default=250, help="Maximum files to scan")
def snapshot_cmd(folder: str, output_dir: str, max_files: int):
    """Export a folder as a portable snapshot directory."""
    print_banner()
    folder_path = Path(folder).resolve()
    out_path = Path(output_dir)
    console.print(f"\n[bold]Exporting snapshot:[/bold] {folder_path}\n")
    export_snapshot(folder_path, out_path, max_files)
    console.print(f"[green]Snapshot written:[/green] {out_path}")
    console.print(f"  receipt.json   — canonical receipt")
    console.print(f"  manifest.json  — snapshot manifest")
    console.print(f"  files.json     — per-file metadata")
    console.print(f"  merkle.json    — Merkle tree structure")
    console.print(f"  proof.json     — per-file Merkle proofs")
    console.print(f"\n[dim]Verify with: bitnet verify-snapshot {out_path}[/dim]\n")


@main.command("verify-snapshot")
@click.argument("snapshot_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def verify_snapshot_cmd(snapshot_dir: str):
    """Verify a portable snapshot directory."""
    print_banner()
    dir_path = Path(snapshot_dir)
    console.print(f"\n[bold]Verifying snapshot:[/bold] {dir_path}\n")
    report = verify_snapshot(dir_path)

    table = Table()
    table.add_column("Check", style="cyan")
    table.add_column("Result", style="green")
    for check, result in report["checks"].items():
        if isinstance(result, bool):
            status = "[green]pass[/]" if result else "[red]FAIL[/]"
        else:
            status = str(result)
        table.add_row(check, status)
    console.print(table)

    if report["valid"]:
        console.print("\n[green]Snapshot is valid and independently verifiable.[/green]\n")
    else:
        console.print("\n[red]Snapshot invalid:[/red]")
        for e in report["errors"]:
            console.print(f"  - {e}")
        console.print()


@main.command()
@click.option("--host", default="127.0.0.1", help="Bind interface (default: 127.0.0.1)")
@click.option("--port", default=8765, type=int, help="Port (default: 8765)")
@click.option("--public", "is_public", is_flag=True, help="Bind 0.0.0.0 (WARNING: exposes filesystem)")
def serve(host: str, port: int, is_public: bool):
    """Launch the web dashboard (localhost by default)."""
    if is_public:
        host = "0.0.0.0"
    else:
        host = "127.0.0.1" if host == "0.0.0.0" else host

    print_banner()
    if host == "0.0.0.0":
        console.print("\n[yellow]WARNING:[/yellow] Binding to 0.0.0.0 — any device on your network can access this dashboard.")
        console.print("        Set BITNET_API_KEY to require authentication.\n")
    console.print(f"\n[green]Dashboard running at http://{host}:{port}[/green]")
    console.print(f"[dim]API key required: {'yes' if os.getenv('BITNET_API_KEY') else 'no (set BITNET_API_KEY to enforce)'}[/dim]\n")
    from bitnet.web import run_server
    run_server(host=host, port=port)


if __name__ == "__main__":
    main()
