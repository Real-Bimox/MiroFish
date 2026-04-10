# MiroFork Sync Workflow Documentation

This document describes how to sync your fork (`Real-Bimox/MiroFish`) with the upstream repository (`666ghj/MiroFish`) while preserving your custom changes.

## Overview

Your fork has significant customizations:
- **Graphiti Integration**: Replaced Zep Cloud with Neo4j/graphiti-core for memory management
- **i18n**: Hardcoded English translations (upstream uses vue-i18n)
- **Local Development**: Custom docker-compose settings for local builds

The upstream repository has:
- **Proper i18n system**: Vue-i18n with translation files and language switching
- **Security updates**: Dependency upgrades
- **Documentation**: Improved README and documentation

## Quick Start

### Option 1: Local Sync Script (Recommended)

Run the sync script from your local repository:

```bash
# Navigate to your repository
cd /path/to/MiroFish

# Make the script executable (first time only)
chmod +x .github/sync-with-upstream.sh

# Run the sync with rebase strategy (preserves your commits on top)
./.github/sync-with-upstream.sh --rebase

# Or use merge strategy (creates a merge commit)
./.github/sync-with-upstream.sh --merge

# Preview what would happen without making changes
./.github/sync-with-upstream.sh --dry-run
```

### Option 2: GitHub Actions (Automated)

1. Go to your repository on GitHub: `https://github.com/Real-Bimox/MiroFish`
2. Navigate to **Actions** → **Sync with Upstream**
3. Click **Run workflow**
4. Choose your preferred sync strategy
5. The workflow will create a Pull Request with the synced changes

### Option 3: Manual Sync

If you prefer full control, follow these manual steps:

```bash
# 1. Add upstream remote (one-time setup)
git remote add upstream https://github.com/666ghj/MiroFish.git

# 2. Fetch upstream changes
git fetch upstream

# 3. Create a backup branch
git branch backup-main-$(date +%Y%m%d)

# 4. Sync using rebase (recommended)
git rebase upstream/main

# Or sync using merge
git merge upstream/main

# 5. Push to your fork
git push origin main
```

## Understanding the Sync Strategies

### Rebase Strategy (Recommended)

**How it works**: Replays your custom commits on top of the latest upstream commits.

**Pros**:
- Clean, linear history
- Your changes appear as if they were made after upstream changes
- Easier to understand the timeline

**Cons**:
- Rewrites commit hashes (requires force push if already pushed)
- Can be more complex to resolve conflicts

**Best for**: Most sync operations, especially when you haven't pushed your changes yet.

### Merge Strategy

**How it works**: Creates a merge commit combining upstream and your changes.

**Pros**:
- Preserves commit hashes
- Easier conflict resolution
- Clear history of when syncs occurred

**Cons**:
- Non-linear history with merge commits
- Can make history harder to follow over time

**Best for**: When you want to preserve exact commit history or when rebase conflicts are complex.

## Handling Conflicts

Conflicts may occur because:
1. Upstream modified files you also changed (i18n translations)
2. Upstream renamed/moved files you modified
3. Both sides made incompatible changes

### Conflict Resolution Steps

When the sync script reports conflicts:

```bash
# 1. See which files have conflicts
git status

# 2. Open each conflicted file and look for conflict markers:
#    <<<<<<< HEAD
#    Your changes
#    =======
#    Upstream changes
#    >>>>>>> upstream/main

# 3. Edit the file to keep the desired changes (remove conflict markers)

# 4. Mark the file as resolved
git add <filename>

# 5. Continue the rebase/merge
# For rebase:
git rebase --continue

# For merge:
git commit

# 6. If you want to abort and start over:
# For rebase:
git rebase --abort

# For merge:
git merge --abort
```

### Common Conflict Scenarios

#### Scenario 1: i18n/Translation Conflicts

**Problem**: Upstream added vue-i18n, your fork has hardcoded English.

**Resolution**: 
- Keep upstream's i18n structure
- Migrate your English translations to the proper i18n files
- Update your components to use `$t()` instead of hardcoded strings

#### Scenario 2: Graphiti vs Zep Cloud

**Problem**: Upstream still uses Zep Cloud, your fork uses Graphiti.

**Resolution**:
- Keep your Graphiti implementation
- Don't overwrite your:
  - `backend/app/services/graphiti_*.py` files
  - `backend/app/graphiti_client.py`
  - Neo4j configuration

#### Scenario 3: docker-compose.yml

**Problem**: Upstream uses pre-built images, you use local builds.

**Resolution**:
- Keep your local build configuration
- Or use environment variables to switch between modes

## Preserving Your Custom Changes

### Critical Files to Protect

These files contain your core customizations. Be extra careful when syncing:

```
backend/app/services/graphiti_tools.py       # Graphiti search tools
backend/app/services/graphiti_paging.py      # Graphiti pagination
backend/app/services/graphiti_entity_reader.py
backend/app/services/graphiti_memory_updater.py
backend/app/services/graphiti_ontology_generator.py
backend/app/services/graphiti_report_agent.py
backend/app/graphiti_client.py               # Graphiti client factory
backend/app/config.py                        # Neo4j config (your version)
docker-compose.yml                           # Local build settings
```

### Creating a Preservation Checklist

Before syncing, review this checklist:

- [ ] Graphiti services are preserved
- [ ] Neo4j configuration is maintained
- [ ] Local docker-compose settings are kept
- [ ] English translations are working

## Automation Setup

### Scheduled Sync (GitHub Actions)

The included workflow runs weekly. To customize:

1. Edit `.github/workflows/sync-upstream.yml`
2. Modify the cron schedule:
   ```yaml
   schedule:
     - cron: '0 0 * * 0'  # Weekly on Sunday
     # - cron: '0 0 * * *'  # Daily
     # - cron: '0 */6 * * *'  # Every 6 hours
   ```

### Pre-Sync Hooks

Create a script to run before syncing:

```bash
#!/bin/bash
# .github/pre-sync-check.sh

echo "Running pre-sync checks..."

# Check for uncommitted changes
if ! git diff --quiet HEAD; then
    echo "⚠️  You have uncommitted changes. Commit or stash them first."
    git status --short
    exit 1
fi

# Run tests
# cd backend && python -m pytest

echo "✅ Pre-sync checks passed"
```

## Troubleshooting

### Issue: " refusing to merge unrelated histories"

**Solution**:
```bash
git merge upstream/main --allow-unrelated-histories
```

### Issue: "Updates were rejected because the tip of your current branch is behind"

**Solution** (if using rebase):
```bash
git push origin main --force-with-lease
```

**Warning**: Only force push if you're sure no one else is working on this branch.

### Issue: Sync script fails with permission denied

**Solution**:
```bash
chmod +x .github/sync-with-upstream.sh
```

### Issue: Conflicts keep recurring

**Solution**: Consider using merge strategy instead of rebase, or create topic branches for upstream syncs:

```bash
# Create a branch for the sync
git checkout -b sync-upstream-$(date +%Y%m%d)
git merge upstream/main
# Test, then merge to main via PR
```

## Best Practices

1. **Sync regularly**: Smaller, frequent syncs are easier than large, infrequent ones
2. **Test after syncing**: Always run your application after syncing
3. **Use feature branches**: Keep custom work in feature branches when possible
4. **Document conflicts**: When you resolve conflicts, document why you chose a particular resolution
5. **Review upstream changes**: Check what changed in upstream before syncing

## Getting Help

If you encounter issues:

1. Check your backup branches: `git branch -a | grep backup`
2. Review the sync script's dry-run output: `./.github/sync-with-upstream.sh --dry-run`
3. Check GitHub issues in both repositories
4. Review Git documentation: https://git-scm.com/doc

## Appendix: Understanding Your Fork's Changes

### Commit History

Your fork contains these major changes not in upstream:

1. **Graphiti Integration** (v0.2.0 - v0.5.x)
   - Replaced Zep Cloud with self-hosted Graphiti + Neo4j
   - New services: graphiti_tools, graphiti_paging, graphiti_entity_reader, etc.
   - Async event loop bridge for Graphiti/Flask

2. **Internationalization** (v0.3.0 - v0.4.x)
   - Hardcoded English translations of Chinese text
   - Note: Upstream uses proper vue-i18n system instead

3. **Version Alignment**
   - Version numbering diverged from upstream
   - Custom CHANGELOG documenting fork changes

### File Differences Summary

```bash
# See all files different from upstream
git diff upstream/main --name-only

# See detailed diff for a specific file
git diff upstream/main -- backend/app/config.py
```

---

**Last updated**: 2026-04-10  
**Upstream**: https://github.com/666ghj/MiroFish  
**Your fork**: https://github.com/Real-Bimox/MiroFish
