import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from navhub.access import AccessModel  # noqa: E402

CFG = ROOT / "sample_config"


def names(model, user):
    return [d.name for d in model.visible_dashboards(user)]


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.m = AccessModel.from_dir(CFG)

    def test_super_admin_sees_everything(self):
        self.assertEqual(len(self.m.visible_dashboards("alice@example.com")), len(self.m.dashboards))

    def test_unknown_user_sees_nothing(self):
        self.assertEqual(names(self.m, "nobody@example.com"), [])

    def test_email_matching_ignores_case_and_spaces(self):
        self.assertEqual(names(self.m, " ALICE@Example.com "), names(self.m, "alice@example.com"))

    def test_cluster_only_grant_is_implicit_all_below(self):
        # Carol has no sub-cluster rows for HSE_HUB, so she sees its dashboard.
        self.assertIn("Incident Tracker", names(self.m, "carol@example.com"))

    def test_subcluster_layer_restricts(self):
        self.assertEqual(names(self.m, "bob@example.com"), ["Berth Utilisation", "Vessel Waiting Time"])

    def test_dashboard_layer_restricts_within_cluster(self):
        got = names(self.m, "carol@example.com")
        self.assertIn("Container Throughput", got)
        self.assertNotIn("Dwell Time", got)
        self.assertNotIn("Vessel Waiting Time", got)

    def test_restriction_rows_are_scoped_to_their_cluster(self):
        # Carol's dashboard allow-list is for OPS_HUB only; HSE_HUB stays unrestricted.
        self.assertIn("Incident Tracker", names(self.m, "carol@example.com"))

    def test_vendor_sees_single_dashboard(self):
        self.assertEqual(names(self.m, "dave@vendor-example.com"), ["Dwell Time"])

    def test_lower_layer_never_widens_higher_layer(self):
        # Dave's sub-cluster layer allows only Cargo. Adding a Berth dashboard row must not unlock it.
        m = AccessModel.from_dir(CFG)
        m.user_dashboards.append({"AppName": "Demo Maritime", "UserEmail": "dave@vendor-example.com",
                                  "ClusterCode": "OPS_HUB", "SubClusterName": "Berth",
                                  "DashboardName": "Berth Utilisation"})
        self.assertEqual(names(m, "dave@vendor-example.com"), ["Dwell Time"])
        self.assertTrue(any("cannot widen" in i for i in m.config_gaps()))

    def test_no_cluster_grant_means_no_access_despite_restriction_rows(self):
        self.assertNotIn("Revenue Summary", names(self.m, "bob@example.com"))

    def test_wildcard_app_and_cluster(self):
        self.assertIn("Fleet Availability", names(self.m, "alice@example.com"))

    def test_sample_config_is_clean(self):
        self.assertEqual(self.m.config_gaps(), [])

    def test_config_gaps_detects_dead_and_unmatched_rows(self):
        m = AccessModel.from_dir(CFG)
        m.user_dashboards.append({"AppName": "Demo Maritime", "UserEmail": "bob@example.com",
                                  "ClusterCode": "FIN_HUB", "SubClusterName": "Cost",
                                  "DashboardName": "Cost Overview"})
        m.user_dashboards.append({"AppName": "Demo Maritime", "UserEmail": "carol@example.com",
                                  "ClusterCode": "OPS_HUB", "SubClusterName": "Cargo",
                                  "DashboardName": "Typo Name"})
        joined = " | ".join(m.config_gaps())
        self.assertIn("dead row", joined)
        self.assertIn("matches nothing", joined)


if __name__ == "__main__":
    unittest.main()
