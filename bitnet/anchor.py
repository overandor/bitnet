"""Optional Solana anchoring — memo transactions on devnet."""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
SOLANA_KEYPAIR_PATH = os.getenv("SOLANA_KEYPAIR_PATH", "")
SOLANA_ENABLED = bool(SOLANA_KEYPAIR_PATH and os.path.exists(SOLANA_KEYPAIR_PATH))
MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
NETWORK_CODE = "SDV"


class AnchorService:
    """Solana memo anchoring. Writes folder Merkle roots as on-chain memos."""

    def __init__(self):
        self.rpc_url = SOLANA_RPC_URL
        self.keypair = None
        self.network_code = NETWORK_CODE
        self._init_keypair()

    def _init_keypair(self):
        if not SOLANA_ENABLED:
            return
        try:
            from solana.keypair import Keypair
            kp_path = Path(SOLANA_KEYPAIR_PATH)
            data = json.loads(kp_path.read_text())
            self.keypair = Keypair.from_secret_key(bytes(data))
        except Exception:
            pass

    @property
    def available(self) -> bool:
        try:
            from solana.rpc.async_api import AsyncClient
            from solana.keypair import Keypair
            return self.keypair is not None
        except ImportError:
            return False

    @property
    def wallet_address(self) -> str:
        if self.keypair:
            return str(self.keypair.pubkey())
        return "not configured"

    async def get_balance(self) -> float:
        if not self.available:
            return 0.0
        try:
            from solana.rpc.async_api import AsyncClient
            from solana.rpc.commitment import Confirmed
            async with AsyncClient(self.rpc_url) as c:
                r = await c.get_balance(self.keypair.pubkey(), commitment=Confirmed)
                return r.value / 1e9
        except Exception:
            return 0.0

    async def _send_memo(self, memo_data: str, max_retries: int = 3) -> Optional[dict]:
        if not self.available:
            return None
        if len(memo_data.encode()) > 566:
            memo_data = memo_data[:560]
        last_error = None
        for attempt in range(max_retries):
            try:
                from solana.rpc.async_api import AsyncClient
                from solana.rpc.commitment import Finalized
                from solana.transaction import Transaction
                from solana.message import Message
                from solana.instruction import Instruction
                from solana.rpc.types import TxOpts
                from solders.pubkey import Pubkey
                from solders.system_program import ID as SYS_PROGRAM_ID
                from solders.hash import Hash as Blockhash

                async with AsyncClient(self.rpc_url) as client:
                    ix = Instruction(
                        program_id=Pubkey.from_string(MEMO_PROGRAM_ID),
                        accounts=[],
                        data=memo_data.encode(),
                    )
                    recent = await client.get_latest_blockhash(commitment=Finalized)
                    bh = recent.value.blockhash
                    msg = Message.new_with_blockhash([ix], self.keypair.pubkey(), bh)
                    tx = Transaction.new_unsigned(msg)
                    tx.sign([self.keypair], bh)
                    result = await client.send_transaction(tx)
                    sig = str(result.value)
                    await asyncio.sleep(1.5)
                    return {
                        "network_code": self.network_code,
                        "network": "solana-devnet",
                        "anchor_tx": sig,
                        "explorer_url": f"https://explorer.solana.com/tx/{sig}?cluster=devnet",
                        "status": "confirmed",
                        "anchored_at": datetime.now(timezone.utc).isoformat(),
                    }
            except Exception as e:
                last_error = str(e)
                if "blockhash" in last_error.lower():
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                break
        return {"network_code": self.network_code, "error": last_error, "status": "failed"}

    async def anchor_folder(
        self,
        root_path: str,
        merkle_root: str,
        files_seen: int,
    ) -> Optional[dict]:
        """Anchor a folder Merkle root as a Solana memo."""
        memo = json.dumps({
            "t": "folder_anchor",
            "root": str(root_path)[-40:],
            "mr": merkle_root.replace("sha256:", "")[:24],
            "n": int(files_seen),
            "ts": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"),
        }, separators=(",", ":"))
        return await self._send_memo(memo)


anchor_service = AnchorService()
