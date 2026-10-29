# Access model

## The three layers

| Layer | Table | Meaning |
|---|---|---|
| 1. Cluster | `UserClusterAccess` | Which clusters a user may enter. Default deny. `ALL` in `AppName` and/or `ClusterCode` is a wildcard for super admins. |
| 2. Sub-cluster | `UserSubClusterAccess` | Optional allow-list of sub-clusters inside a cluster. |
| 3. Dashboard | `UserDashboardAccess` | Optional allow-list of individual dashboards inside a cluster. |

Layers 2 and 3 are **restrict-only**:

- no rows for a user in a cluster means the layer is inactive ("implicit ALL")
- one or more rows means that layer becomes an explicit allow-list for that user and cluster
- a dashboard is visible only if it survives every active layer, so a lower layer can never widen what a higher layer already removed

## Why restrict-only?

The common case is "this person gets the whole cluster". Storing only the exceptions keeps the tables small: a user with full access to a cluster needs one row, not one row per dashboard. When a dashboard is added to the index, everyone with unrestricted access gets it without any config change, and only the few restricted users need a decision.

The cost is that a single restriction row flips a user from "everything" to "only what is listed", for the whole cluster. This is easy to do by accident, which is why `navhub check` exists.

## Worked example (sample_config)

| User | Rows | Result |
|---|---|---|
| alice | cluster `ALL`/`ALL` | every dashboard in every app |
| bob | cluster OPS_HUB + sub-cluster Berth | the two Berth dashboards |
| carol | clusters OPS_HUB and HSE_HUB, dashboard list for OPS_HUB | the two listed OPS dashboards plus everything in HSE_HUB (the list only applies to OPS_HUB) |
| dave (external) | cluster OPS_HUB + sub-cluster Cargo + dashboard Dwell Time | one dashboard |
| nobody | none | nothing |

## Things the lint catches

- a dashboard in an allow-list that does not exist in `DashboardIndex` (typo or renamed dashboard)
- restriction rows for a cluster the user was never granted (dead rows)
- a dashboard allow-list entry in a sub-cluster that layer 2 already hides

## Design notes

- Key on stable identifiers. In a real model, join datasets by GUID rather than by name, because names repeat across workspaces and dev/test copies silently multiply rows.
- Compare emails case-insensitively and trim spaces. Config is typed by people.
- Group-based membership (security groups) scales better than per-user rows. The same funnel works with a group key in place of `UserEmail`, with group membership expanded before the lookup.
- Auditing "who has access to what" needs the group members expanded, or counts are undercounted.
