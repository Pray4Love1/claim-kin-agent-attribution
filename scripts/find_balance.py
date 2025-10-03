 #!/usr/bin/env python3
 """Report the withdrawable USD balance for a Hyperliquid account."""
 from __future__ import annotations
 
 import argparse
 import json
 import sys
 from decimal import Decimal, ROUND_HALF_UP
 from typing import Sequence
 
 from hyperliquid.info import Info
 
 from claim_kin_agent_attribution.balances import extract_withdrawable_balance
 
 def _build_parser() -> argparse.ArgumentParser:
     parser = argparse.ArgumentParser(
         description="Fetch the withdrawable USD balance for a Hyperliquid account."
     )
     parser.add_argument("address", help="Hyperliquid account address (0x...)")
     parser.add_argument(
         "--dex",
         default="",
         help="Optional DEX identifier to pass through to the API.",
     )
     parser.add_argument(
         "--json",
         action="store_true",
         help="Emit JSON instead of a formatted string.",
     )
     return parser
 
 def _format_amount(value: Decimal) -> str:
     return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,}"
 
 def main(argv: Sequence[str] | None = None) -> int:
     parser = _build_parser()
     args = parser.parse_args(argv)
 
     info = Info(skip_ws=True)
     user_state = info.user_state(address=args.address, dex=args.dex)
     balance = extract_withdrawable_balance(user_state)
 
     if args.json:
         json.dump(
             {
                 "address": args.address,
                 "dex": args.dex or None,
                 "withdrawable_usd": str(balance),
             },
             sys.stdout,
             indent=2,
         )
         sys.stdout.write("\n")
         return 0
 
     formatted = _format_amount(balance)
     print(f"Withdrawable balance for {args.address}: ${formatted} USD")
     return 0
     