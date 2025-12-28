# github-metrics (create-report)

A tool to compare and analyze personal GitHub activity on a yearly basis (e.g., 2024 vs 2025).

## Quick Start

You can run it directly from the repository using `uv`. By default, it analyzes the **current year and the previous year**.

```bash
export GITHUB_TOKEN=your_token
# Default execution (Last year & This year)
uvx --from git+https://github.com/laiso/github-metrics create-report

# Specify target years
uvx --from git+https://github.com/laiso/github-metrics create-report --year 2023 2024 2025
```

*Note: Requires `GITHUB_TOKEN` or authentication via the `gh` CLI.*

## Metrics (Strict Mode)

Accurate metrics aggregated using the GitHub GraphQL API.

| Metric | Definition | Note |
| :--- | :--- | :--- |
| **Commits** | Number of commits authored by you | Scans the history of the default branch |
| **PRs** | Number of Pull Requests created | |
| **Merged** | Number of PRs **created and merged** by you | Counted as your activity |
| **Issues** | Number of Issues created | PRs are excluded |

## Features

- **Accurate Aggregation**: Avoids Search API limitations by strictly scanning each repository's history.
- **Multi-year Comparison**: Displays data for multiple years side-by-side.
- **Multi-format Output**: Generates `out/metrics_report.json` and `out/metrics_report.csv` in addition to stdout.

## Notes

- This tool is intended for personal reflection and self-analysis.
- Commit counts depend on development style and are not a simple indicator of productivity.
