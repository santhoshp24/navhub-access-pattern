import argparse
import sys
from pathlib import Path

from .access import AccessModel

DEFAULT = Path(__file__).resolve().parents[2] / "sample_config"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="navhub", description="Resolve dashboard visibility for a user.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resolve", help="list the dashboards a user can see")
    r.add_argument("user")
    r.add_argument("--config", default=str(DEFAULT))
    c = sub.add_parser("check", help="lint the config tables")
    c.add_argument("--config", default=str(DEFAULT))
    a = ap.parse_args(argv)
    model = AccessModel.from_dir(a.config)
    if a.cmd == "resolve":
        rows = model.visible_dashboards(a.user)
        if not rows:
            print(f"{a.user}: no dashboards visible")
        for d in rows:
            print(f"{d.app} > {d.cluster} > {d.subcluster} > {d.name}")
        return 0
    issues = model.config_gaps()
    for i in issues:
        print("-", i)
    print(f"{len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
