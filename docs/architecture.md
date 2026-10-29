# Architecture

A navigation hub gives many dashboards a single, branded entry point and shows each person only what they are entitled to.

## Five tiers

```
App gallery -> Landing page -> Sub-cluster -> Dashboard index -> Dashboard
   (apps)      (clusters)      (groups)        (list)            (report)
```

- **Config-driven.** Clusters, sub-clusters and dashboards are rows in config tables, not hand-built pages. Adding a dashboard is adding a row.
- **One list, scoped by `AppName`.** One set of tables serves several apps instead of one list per app. An app that has no sub-cluster level simply uses fewer layers.
- **Cards are rendered from data.** A measure builds HTML for each card (title, icon, link) and an HTML-rendering visual displays the grid. Icons are embedded as base64 so there are no external image dependencies.
- **Rank-based slots** compact the card grid so hidden dashboards do not leave gaps.
- **`IconTheme`** (Light/Dark) on the cluster config picks icon colours that stay readable on light and dark page backgrounds.

## Security

Visibility is enforced with row-level security on the config tables, driven by the three-layer funnel in [access-model.md](access-model.md). The hub only lists what the user may open; the underlying reports and datasets keep their own permissions.

## Operating it

- Config lives in a versioned workbook (or list) with a gap-check sheet, so changes are reviewed like code.
- An audit pipeline (PowerShell against the Power BI and Graph APIs) exports datasets, reports, RLS roles, group members and refresh status into CSVs, which a Power Query chain classifies. It answers "who can see what, and are they still active".
- Onboarding and offboarding are formalised against the config tables, ideally through security-group membership.

## Practical lessons

- Some Power BI features people expect do not exist: conditional formatting for button visibility, header toggles on table visuals, navigation actions on button slicers. Check before designing around them.
- A static canvas background per page beats per-card backgrounds.
- Use authentic transparent logo assets rather than extracting logos programmatically.
- Long audit loops outlive access tokens (roughly an hour). Check expiry before loops.
- Some authentication libraries conflict when loaded in one PowerShell process. Separate windows for the Power BI and Graph calls avoids it.
- Format dates explicitly before exporting CSVs; defaults follow the machine's regional settings.
- Excel files on shared storage can accumulate phantom blank columns that break refresh; delete the excess columns.
