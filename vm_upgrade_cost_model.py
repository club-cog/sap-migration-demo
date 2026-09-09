"""Fleet upgrade cost model: ACUs and USD for Devin-assisted upgrades of ~3,918 servers.

Edit the ASSUMPTIONS block, then run:

    python vm_upgrade_cost_model.py            # prints markdown tables
    python vm_upgrade_cost_model.py --csv out  # also writes out.csv

Cost formula per server type and scenario (mid / high):

    acus = server_count * sessions_per_server * acus_per_session * retry_overhead
    usd  = acus * price_per_acu

See vm-upgrade-cost-estimate.md for the narrative and the source of each assumption.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# ASSUMPTIONS (tune here)
# --------------------------------------------------------------------------- #

SCENARIOS = ("mid", "high")

# Price per ACU in USD used for cost projections.
PRICE_PER_ACU = {
    "projection_1.667": 1.667,
}

# Multiplier for failed / re-run sessions (1.20 = 20% of session spend is retries).
RETRY_OVERHEAD = {"mid": 1.20, "high": 1.35}


@dataclass(frozen=True)
class Tier:
    name: str
    sessions_per_server: tuple[float, float]  # mid, high
    acus_per_session: tuple[float, float]  # mid, high
    review_hours_per_server: tuple[float, float]  # human effort, not billed in ACUs
    size_label: str  # dim_sessions size tier the mid ACU value sits in


TIERS = {
    "os": Tier(
        name="OS upgrade",
        sessions_per_server=(1.0, 2.0),
        acus_per_session=(16, 30),
        review_hours_per_server=(0.5, 1.0),
        size_label="M-L",
    ),
    "middleware": Tier(
        name="App server / middleware",
        sessions_per_server=(2.0, 3.0),
        acus_per_session=(30, 50),
        review_hours_per_server=(1.0, 2.0),
        size_label="L-XL",
    ),
    "database": Tier(
        name="Database",
        sessions_per_server=(3.0, 5.0),
        acus_per_session=(50, 80),
        review_hours_per_server=(2.0, 4.0),
        size_label="XL",
    ),
    "pega": Tier(
        name="Pega platform",
        sessions_per_server=(4.0, 6.0),
        acus_per_session=(60, 100),
        review_hours_per_server=(2.0, 4.0),
        size_label="XL",
    ),
}

# (server type, tier key, count) from the source inventory ("Count of Server Name").
INVENTORY = [
    ("RHEL7", "os", 1566),
    ("Windows 2016", "os", 1102),
    ("Windows 2012", "os", 22),
    ("RHEL6", "os", 12),
    ("JWS v5", "middleware", 405),
    ("JBOSS EAP v7.x", "middleware", 230),
    ("Confluent Kafka", "middleware", 147),
    ("MQ Mod", "middleware", 47),
    ("WAS Liberty v21.x", "middleware", 20),
    ("WAS7", "middleware", 5),
    ("SQL2016", "database", 120),
    ("SQL2017", "database", 48),
    ("Oracle12c", "database", 18),
    ("Pega v24.1", "pega", 63),
    ("Pega v8.8", "pega", 60),
    ("Pega v24.2", "pega", 33),
    ("Pega v7.x", "pega", 13),
    ("Pega v23.1", "pega", 7),
]

EXPECTED_TOTAL = 3918

# --------------------------------------------------------------------------- #
# MODEL
# --------------------------------------------------------------------------- #


@dataclass
class Row:
    server_type: str
    tier: str
    count: int
    acus: dict[str, float]
    review_hours: dict[str, float]

    def usd(self, scenario: str, price: float) -> float:
        return self.acus[scenario] * price


def compute_rows() -> list[Row]:
    rows = []
    for server_type, tier_key, count in INVENTORY:
        tier = TIERS[tier_key]
        acus = {}
        hours = {}
        for i, s in enumerate(SCENARIOS):
            acus[s] = count * tier.sessions_per_server[i] * tier.acus_per_session[i] * RETRY_OVERHEAD[s]
            hours[s] = count * tier.review_hours_per_server[i]
        rows.append(Row(server_type, tier_key, count, acus, hours))
    return rows


def subtotal(rows: list[Row]) -> Row:
    return Row(
        server_type="Subtotal",
        tier=rows[0].tier if rows else "",
        count=sum(r.count for r in rows),
        acus={s: sum(r.acus[s] for r in rows) for s in SCENARIOS},
        review_hours={s: sum(r.review_hours[s] for r in rows) for s in SCENARIOS},
    )


def fmt_int(x: float) -> str:
    return f"{x:,.0f}"


def fmt_usd(x: float) -> str:
    return f"${x:,.0f}"


def print_markdown(rows: list[Row]) -> None:
    total = sum(r.count for r in rows)
    if total != EXPECTED_TOTAL:
        print(f"WARNING: inventory sums to {total}, expected {EXPECTED_TOTAL}", file=sys.stderr)

    print("### Assumptions per tier\n")
    print("| Tier | Sessions/server (M/H) | ACUs/session (M/H) | dim_sessions size | Review hrs/server (M/H) |")
    print("|---|---|---|---|---|")
    for t in TIERS.values():
        print(
            f"| {t.name} | {' / '.join(str(x) for x in t.sessions_per_server)} | "
            f"{' / '.join(str(x) for x in t.acus_per_session)} | {t.size_label} | "
            f"{' / '.join(str(x) for x in t.review_hours_per_server)} |"
        )
    print(f"\nRetry overhead multiplier: {RETRY_OVERHEAD['mid']} / {RETRY_OVERHEAD['high']}\n")

    for price_key, price in PRICE_PER_ACU.items():
        print(f"### Cost by server type at ${price:.3f}/ACU ({price_key})\n")
        print("| Server type | Tier | Servers | ACUs mid | ACUs high | USD mid | USD high | % of mid ACUs |")
        print("|---|---|---:|---:|---:|---:|---:|---:|")
        grand = subtotal(rows)
        for tier_key, tier in TIERS.items():
            tier_rows = [r for r in rows if r.tier == tier_key]
            for r in tier_rows:
                print(
                    f"| {r.server_type} | {tier.name} | {r.count:,} | {fmt_int(r.acus['mid'])} | "
                    f"{fmt_int(r.acus['high'])} | {fmt_usd(r.usd('mid', price))} | "
                    f"{fmt_usd(r.usd('high', price))} | {r.acus['mid'] / grand.acus['mid']:.1%} |"
                )
            st = subtotal(tier_rows)
            print(
                f"| **Subtotal: {tier.name}** | | **{st.count:,}** | **{fmt_int(st.acus['mid'])}** | "
                f"**{fmt_int(st.acus['high'])}** | **{fmt_usd(st.usd('mid', price))}** | "
                f"**{fmt_usd(st.usd('high', price))}** | **{st.acus['mid'] / grand.acus['mid']:.1%}** |"
            )
        print(
            f"| **Grand total** | | **{grand.count:,}** | **{fmt_int(grand.acus['mid'])}** | "
            f"**{fmt_int(grand.acus['high'])}** | **{fmt_usd(grand.usd('mid', price))}** | "
            f"**{fmt_usd(grand.usd('high', price))}** | 100% |"
        )
        print()

    grand = subtotal(rows)
    print("### Grand total\n")
    print("| Scenario | ACUs | " + " | ".join(f"USD @ ${p:.3f}" for p in PRICE_PER_ACU.values()) + " | Human review hours |")
    print("|---|---:|" + "---:|" * len(PRICE_PER_ACU) + "---:|")
    for s in SCENARIOS:
        print(
            f"| {s} | {fmt_int(grand.acus[s])} | "
            + " | ".join(fmt_usd(grand.usd(s, p)) for p in PRICE_PER_ACU.values())
            + f" | {fmt_int(grand.review_hours[s])} |"
        )
    print()

    print("### Efficiency metrics (mid scenario)\n")
    mid_sessions = sum(
        r.count * TIERS[r.tier].sessions_per_server[SCENARIOS.index("mid")] * RETRY_OVERHEAD["mid"] for r in rows
    )
    print(f"- Sessions (incl. retries): {fmt_int(mid_sessions)}")
    print(f"- ACUs per server: {grand.acus['mid'] / grand.count:.1f}")
    print(f"- Servers upgraded per 1K ACUs: {1000 * grand.count / grand.acus['mid']:.1f}")
    print(f"- Human review hours per 1K ACUs: {1000 * grand.review_hours['mid'] / grand.acus['mid']:.1f}")


def write_csv(rows: list[Row], path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        header = ["server_type", "tier", "server_count"]
        for s in SCENARIOS:
            header += [
                f"sessions_per_server_{s}",
                f"acus_per_session_{s}",
                f"retry_overhead_{s}",
                f"acus_{s}",
                f"review_hours_{s}",
            ]
            header += [f"usd_{s}_at_{p:.3f}" for p in PRICE_PER_ACU.values()]
        w.writerow(header)

        def emit(r: Row, label: str | None = None, tier_label: str | None = None) -> None:
            tier = TIERS[r.tier]
            out = [label or r.server_type, tier_label or tier.name, r.count]
            for i, s in enumerate(SCENARIOS):
                out += [
                    tier.sessions_per_server[i] if label is None else "",
                    tier.acus_per_session[i] if label is None else "",
                    RETRY_OVERHEAD[s],
                    round(r.acus[s], 1),
                    round(r.review_hours[s], 1),
                ]
                out += [round(r.usd(s, p), 2) for p in PRICE_PER_ACU.values()]
            w.writerow(out)

        for tier_key, tier in TIERS.items():
            tier_rows = [r for r in rows if r.tier == tier_key]
            for r in tier_rows:
                emit(r)
            emit(subtotal(tier_rows), label=f"SUBTOTAL {tier.name}")
        grand = subtotal(rows)
        grand.tier = "os"  # placeholder so emit() can resolve a Tier; label overrides the name
        emit(grand, label="GRAND TOTAL", tier_label="all")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", metavar="PATH", help="also write the per-type table to this CSV file")
    args = parser.parse_args()
    rows = compute_rows()
    print_markdown(rows)
    if args.csv:
        write_csv(rows, args.csv)
        print(f"\nWrote {args.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
