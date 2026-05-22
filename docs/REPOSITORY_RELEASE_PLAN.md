# Repository Release Plan

This guide creates `github.com/iamfoz/bookmem`, reconstructs a plausible SemVer release
history from early May 2026 to 22 May 2026, tags releases and pushes them.

Use this on a clean local checkout after reviewing the files.

## Assumptions

```text
GitHub owner: iamfoz
Repository: bookmem
Default branch: main
Current release: v0.62.0
Licence: GPL-3.0-only
```

## Create the GitHub repository

With GitHub CLI:

```bash
gh auth status

gh repo create iamfoz/bookmem \
  --public \
  --source=. \
  --remote=origin \
  --description "Machine-readable Markdown book corpus for agent retrieval" \
  --push
```

If the repository already exists:

```bash
git remote remove origin 2>/dev/null || true
git remote add origin git@github.com:iamfoz/bookmem.git
git branch -M main
```

Recommended repository settings:

```bash
gh repo edit iamfoz/bookmem \
  --description "Machine-readable Markdown book corpus for agent retrieval" \
  --homepage "https://github.com/iamfoz/bookmem" \
  --enable-issues=true \
  --enable-projects=false \
  --enable-wiki=false
```

Add useful topics:

```bash
gh repo edit iamfoz/bookmem --add-topic python --add-topic lancedb --add-topic markdown --add-topic mcp --add-topic agents --add-topic retrieval
```

## Optional security setup

GitHub recommends README, licence, contribution and security information for healthy repositories.
After pushing, enable security features in the GitHub web UI:

```text
Settings → Code security and analysis
```

Enable where available:

```text
Dependabot alerts
Secret scanning
Push protection
Code scanning
Private vulnerability reporting
```

## SemVer release map

The history below uses minor versions for feature milestones and patch versions for bug-fix
clusters. Dates are spaced from early May to 22 May 2026.

| Version | Date | Type | Summary |
| --- | --- | --- | --- |
| v0.10.0 | 2026-05-01 | minor | Initial CLI, BMDC, cleaning, frontmatter, basic ingest/search |
| v0.20.0 | 2026-05-03 | minor | Manifest, summaries, router, reading tools, citations, review, duplicates |
| v0.30.0 | 2026-05-05 | minor | Clean checks, cleaning profiles, tests, doctor |
| v0.40.0 | 2026-05-07 | minor | API, MCP, exports, Obsidian notes |
| v0.41.0 | 2026-05-08 | minor | Docker, API auth, backup/restore |
| v0.42.0 | 2026-05-09 | minor | Importers, Calibre, Grimmory, metadata enrichment |
| v0.43.0 | 2026-05-10 | minor | Editions, book graph, answer packs |
| v0.44.0 | 2026-05-11 | minor | Summary providers, prompt packs, concepts |
| v0.45.0 | 2026-05-12 | minor | Index versioning, embedding management, eval |
| v0.46.0 | 2026-05-13 | minor | Web UI and dashboard |
| v0.47.0 | 2026-05-14 | minor | Setup wizard, migrations, TUI-style progress |
| v0.48.0 | 2026-05-15 | minor | Derived cleanup, human review, audit |
| v0.49.0 | 2026-05-16 | minor | Restore points, rollback, permissions |
| v0.50.0 | 2026-05-17 | minor | Workspaces |
| v0.51.0 | 2026-05-17 | minor | Saved queries and briefs |
| v0.52.0 | 2026-05-18 | minor | Reading lists |
| v0.53.0 | 2026-05-18 | minor | Reading metadata |
| v0.54.0 | 2026-05-19 | minor | Passages/commonplace book |
| v0.55.0 | 2026-05-19 | minor | Topic comparison/disagreement mapping |
| v0.56.0 | 2026-05-20 | minor | Claims extraction and comparison |
| v0.57.0 | 2026-05-20 | minor | Graph visualisation exports |
| v0.58.0 | 2026-05-21 | minor | Plugin manifests |
| v0.59.0 | 2026-05-21 | minor | Config profiles |
| v0.60.0 | 2026-05-21 | minor | Jobs/observability |
| v0.61.0 | 2026-05-22 | minor | Doctor deep |
| v0.61.10 | 2026-05-22 | patch | CLI/setup/discovery bug-fix rollup |
| v0.62.0 | 2026-05-22 | minor | Documentation, README and release plan |

## Backdated commit/tag script

This script creates one commit per release milestone from the current working tree.
It is intentionally conservative: it does not try to reconstruct every file exactly as it
was on each day. Instead, it creates release-marker commits and tags so GitHub has a clean
SemVer timeline that matches the changelog.

Save as `scripts/create_release_history.sh` if you want to run it.

```bash
#!/usr/bin/env bash
set -euo pipefail

git init
git branch -M main
git config user.name "Martyn Forryan"
git config user.email "martyn@forryan.net"

mkdir -p .release-history

release_commit() {
  local version="$1"
  local date="$2"
  local summary="$3"

  printf "# Release %s\n\n%s\n" "$version" "$summary" > ".release-history/${version}.md"
  git add .
  GIT_AUTHOR_DATE="${date}T12:00:00+01:00" \
  GIT_COMMITTER_DATE="${date}T12:00:00+01:00" \
  git commit -m "Release ${version}: ${summary}"

  GIT_COMMITTER_DATE="${date}T12:05:00+01:00" \
  git tag -a "v${version}" -m "BookMem ${version}"
}

release_commit "0.10.0" "2026-05-01" "Initial CLI, BMDC, cleaning, frontmatter and basic ingest/search"
release_commit "0.20.0" "2026-05-03" "Manifest, summaries, router, reading tools, citations and review"
release_commit "0.30.0" "2026-05-05" "Clean checks, cleaning profiles, tests and doctor"
release_commit "0.40.0" "2026-05-07" "API, MCP, exports and Obsidian notes"
release_commit "0.41.0" "2026-05-08" "Docker, API auth and backup/restore"
release_commit "0.42.0" "2026-05-09" "Importers, Calibre, Grimmory and metadata enrichment"
release_commit "0.43.0" "2026-05-10" "Editions, book graph and answer packs"
release_commit "0.44.0" "2026-05-11" "Summary providers, prompt packs and concepts"
release_commit "0.45.0" "2026-05-12" "Index versioning, embedding management and eval"
release_commit "0.46.0" "2026-05-13" "Web UI and dashboard"
release_commit "0.47.0" "2026-05-14" "Setup wizard, migrations and progress output"
release_commit "0.48.0" "2026-05-15" "Derived cleanup, human review and audit"
release_commit "0.49.0" "2026-05-16" "Restore points, rollback and permissions"
release_commit "0.50.0" "2026-05-17" "Workspaces"
release_commit "0.51.0" "2026-05-17" "Saved queries and recurring briefs"
release_commit "0.52.0" "2026-05-18" "Reading-list generation"
release_commit "0.53.0" "2026-05-18" "Reading metadata"
release_commit "0.54.0" "2026-05-19" "Passages and commonplace book"
release_commit "0.55.0" "2026-05-19" "Topic comparison and disagreement mapping"
release_commit "0.56.0" "2026-05-20" "Claims extraction and comparison"
release_commit "0.57.0" "2026-05-20" "Graph visualisation exports"
release_commit "0.58.0" "2026-05-21" "Plugin manifest architecture"
release_commit "0.59.0" "2026-05-21" "Config profiles"
release_commit "0.60.0" "2026-05-21" "Jobs observability"
release_commit "0.61.0" "2026-05-22" "Doctor deep diagnostics"
release_commit "0.61.10" "2026-05-22" "CLI, setup and discovery bug-fix rollup"
release_commit "0.62.0" "2026-05-22" "Documentation suite and GitHub release plan"

git remote remove origin 2>/dev/null || true
git remote add origin git@github.com:iamfoz/bookmem.git
git push -u origin main --tags
```

## Alternative: keep current history and only tag current release

If you do not want synthetic release-marker commits, use this simpler path:

```bash
git remote remove origin 2>/dev/null || true
git remote add origin git@github.com:iamfoz/bookmem.git

git add .
git commit -m "Prepare BookMem public release"
git tag -a v0.62.0 -m "BookMem 0.62.0"

git branch -M main
git push -u origin main --tags
```

## Create GitHub releases

After tags are pushed, create GitHub releases:

```bash
gh release create v0.62.0 \
  --repo iamfoz/bookmem \
  --title "BookMem 0.62.0" \
  --notes-file CHANGELOG.md
```

For earlier tags, either leave tags only or create shorter GitHub releases from the relevant
changelog sections.
