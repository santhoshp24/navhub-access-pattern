"""Resolve which dashboards a user may see.

Model (see docs/access-model.md):

  Layer 1  UserClusterAccess      which clusters the user may enter (default deny, 'ALL' wildcard)
  Layer 2  UserSubClusterAccess   optional allow-list of sub-clusters inside a cluster
  Layer 3  UserDashboardAccess    optional allow-list of dashboards inside a cluster

Layers 2 and 3 are *restrict-only*: with no rows for a user in a cluster the layer is
"implicit ALL" (it does not restrict); with one or more rows it becomes an explicit
allow-list. A dashboard is visible only if it survives every active layer, so a lower
layer can never widen what a higher layer already removed.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

WILDCARD = "ALL"


def _norm(s: str) -> str:
    return (s or "").strip().casefold()


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


@dataclass(frozen=True)
class Dashboard:
    app: str
    cluster: str
    subcluster: str
    name: str
    url: str
    sort_order: int


class AccessModel:
    def __init__(self, clusters, dashboards, user_clusters, user_subclusters, user_dashboards):
        self.clusters = clusters
        self.dashboards = dashboards
        self.user_clusters = user_clusters
        self.user_subclusters = user_subclusters
        self.user_dashboards = user_dashboards

    @classmethod
    def from_dir(cls, directory) -> "AccessModel":
        d = Path(directory)
        dashboards = [
            Dashboard(r["AppName"], r["ClusterCode"], r["SubClusterName"], r["DashboardName"],
                      r["ReportURL"], int(r["SortOrder"] or 0))
            for r in _read(d / "DashboardIndex.csv")
        ]
        return cls(_read(d / "ClusterConfig.csv"), dashboards,
                   _read(d / "UserClusterAccess.csv"),
                   _read(d / "UserSubClusterAccess.csv"),
                   _read(d / "UserDashboardAccess.csv"))

    # ---- layer 1 -------------------------------------------------------------
    def _cluster_allowed(self, user: str, app: str, cluster: str) -> bool:
        for r in self.user_clusters:
            if _norm(r["UserEmail"]) != user:
                continue
            app_ok = _norm(r["AppName"]) in (_norm(WILDCARD), _norm(app))
            cl_ok = _norm(r["ClusterCode"]) in (_norm(WILDCARD), _norm(cluster))
            if app_ok and cl_ok:
                return True
        return False

    # ---- layers 2 and 3: restrict-only ---------------------------------------
    def _rows(self, table, user, app, cluster):
        return [r for r in table
                if _norm(r["UserEmail"]) == user and _norm(r["AppName"]) == _norm(app)
                and _norm(r["ClusterCode"]) == _norm(cluster)]

    def visible_dashboards(self, user_email: str) -> list[Dashboard]:
        user = _norm(user_email)
        out = []
        for d in self.dashboards:
            if not self._cluster_allowed(user, d.app, d.cluster):
                continue
            sub_rows = self._rows(self.user_subclusters, user, d.app, d.cluster)
            if sub_rows and _norm(d.subcluster) not in {_norm(r["SubClusterName"]) for r in sub_rows}:
                continue
            dash_rows = self._rows(self.user_dashboards, user, d.app, d.cluster)
            if dash_rows and (_norm(d.subcluster), _norm(d.name)) not in {
                    (_norm(r["SubClusterName"]), _norm(r["DashboardName"])) for r in dash_rows}:
                continue
            out.append(d)
        return sorted(out, key=lambda x: (x.app, x.cluster, x.subcluster, x.sort_order, x.name))

    def config_gaps(self) -> list[str]:
        """Basic hygiene checks on the config tables."""
        issues = []
        known = {(_norm(c["AppName"]), _norm(c["ClusterCode"])) for c in self.clusters}
        dash_keys = {(_norm(d.app), _norm(d.cluster), _norm(d.subcluster), _norm(d.name)) for d in self.dashboards}
        for d in self.dashboards:
            if (_norm(d.app), _norm(d.cluster)) not in known:
                issues.append(f"dashboard '{d.name}' points at unknown cluster {d.app}/{d.cluster}")
        for r in self.user_dashboards:
            if (_norm(r["AppName"]), _norm(r["ClusterCode"]), _norm(r["SubClusterName"]),
                    _norm(r["DashboardName"])) not in dash_keys:
                issues.append(f"{r['UserEmail']}: dashboard allow-list entry '{r['DashboardName']}' "
                              f"matches nothing in DashboardIndex")
        for r in self.user_dashboards + self.user_subclusters:
            if not self._cluster_allowed(_norm(r["UserEmail"]), r["AppName"], r["ClusterCode"]):
                issues.append(f"{r['UserEmail']}: restriction row for {r['ClusterCode']} has no "
                              f"cluster grant (dead row)")
        for r in self.user_dashboards:
            user, app, cl = _norm(r["UserEmail"]), r["AppName"], r["ClusterCode"]
            sub_rows = self._rows(self.user_subclusters, user, app, cl)
            if sub_rows and _norm(r["SubClusterName"]) not in {_norm(x["SubClusterName"]) for x in sub_rows}:
                issues.append(f"{r['UserEmail']}: dashboard '{r['DashboardName']}' sits in sub-cluster "
                              f"'{r['SubClusterName']}', which the sub-cluster layer already hides "
                              f"(a lower layer cannot widen a higher one)")
        return issues
