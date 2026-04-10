#!/bin/bash
#
# Sync fork with upstream repository
# This script synchronizes your fork with the upstream source while preserving your custom changes
#
# Usage: ./sync-with-upstream.sh [options]
#   Options:
#     --rebase     Use rebase strategy (default)
#     --merge      Use merge strategy
#     --dry-run    Show what would happen without making changes
#     --help       Show this help message
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
UPSTREAM_URL="https://github.com/666ghj/MiroFish"
UPSTREAM_BRANCH="main"
LOCAL_BRANCH="main"
BACKUP_BRANCH_PREFIX="backup-before-sync"
STRATEGY="rebase"
DRY_RUN=false

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show help
show_help() {
    head -n 15 "$0" | tail -n 13
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --rebase)
            STRATEGY="rebase"
            shift
            ;;
        --merge)
            STRATEGY="merge"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Function to check if upstream remote exists
check_upstream_remote() {
    if ! git remote | grep -q "^upstream$"; then
        print_info "Adding upstream remote: $UPSTREAM_URL"
        if [ "$DRY_RUN" = false ]; then
            git remote add upstream "$UPSTREAM_URL"
        else
            print_info "[DRY-RUN] Would add upstream remote"
        fi
    else
        print_info "Upstream remote already exists"
        local current_url
        current_url=$(git remote get-url upstream)
        if [ "$current_url" != "$UPSTREAM_URL" ]; then
            print_warning "Upstream URL differs. Updating..."
            if [ "$DRY_RUN" = false ]; then
                git remote set-url upstream "$UPSTREAM_URL"
            else
                print_info "[DRY-RUN] Would update upstream URL"
            fi
        fi
    fi
}

# Function to fetch upstream
fetch_upstream() {
    print_info "Fetching from upstream..."
    if [ "$DRY_RUN" = false ]; then
        git fetch upstream
    else
        print_info "[DRY-RUN] Would fetch from upstream"
    fi
}

# Function to create backup branch
create_backup() {
    local backup_branch="${BACKUP_BRANCH_PREFIX}-$(date +%Y%m%d-%H%M%S)"
    print_info "Creating backup branch: $backup_branch"
    if [ "$DRY_RUN" = false ]; then
        git branch "$backup_branch"
        print_success "Backup created: $backup_branch"
    else
        print_info "[DRY-RUN] Would create backup branch: $backup_branch"
    fi
    echo "$backup_branch"
}

# Function to show commit summary
show_commit_summary() {
    print_info "=== Commit Summary ==="
    
    local upstream_commits
    local local_commits
    
    upstream_commits=$(git log --oneline HEAD..upstream/$UPSTREAM_BRANCH 2>/dev/null | wc -l)
    local_commits=$(git log --oneline upstream/$UPSTREAM_BRANCH..HEAD 2>/dev/null | wc -l)
    
    echo "  Commits in upstream but not in your fork: $upstream_commits"
    echo "  Commits in your fork but not in upstream: $local_commits"
    
    if [ "$upstream_commits" -gt 0 ]; then
        echo ""
        print_info "Upstream commits to be synced:"
        git log --oneline HEAD..upstream/$UPSTREAM_BRANCH | head -20
        if [ "$upstream_commits" -gt 20 ]; then
            echo "  ... and $((upstream_commits - 20)) more commits"
        fi
    fi
}

# Function to sync using rebase
sync_rebase() {
    print_info "Using rebase strategy..."
    
    # Stash any uncommitted changes
    local stash_created=false
    if ! git diff --quiet HEAD; then
        print_warning "Uncommitted changes detected. Stashing..."
        if [ "$DRY_RUN" = false ]; then
            git stash push -m "Auto-stash before sync $(date +%Y%m%d-%H%M%S)"
            stash_created=true
        else
            print_info "[DRY-RUN] Would stash uncommitted changes"
        fi
    fi
    
    # Create backup
    local backup_branch
    backup_branch=$(create_backup)
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would rebase upstream/$UPSTREAM_BRANCH onto $LOCAL_BRANCH"
        if [ "$stash_created" = true ]; then
            print_info "[DRY-RUN] Would pop stashed changes"
        fi
        return
    fi
    
    # Perform rebase
    print_info "Rebasing onto upstream/$UPSTREAM_BRANCH..."
    if git rebase upstream/$UPSTREAM_BRANCH; then
        print_success "Rebase completed successfully!"
    else
        print_error "Rebase has conflicts. Please resolve them manually."
        echo ""
        echo "Conflict resolution steps:"
        echo "  1. Resolve conflicts in the affected files"
        echo "  2. Run: git add <resolved-files>"
        echo "  3. Run: git rebase --continue"
        echo "  4. If you want to abort: git rebase --abort"
        echo ""
        echo "Your original branch is backed up as: $backup_branch"
        exit 1
    fi
    
    # Pop stash if created
    if [ "$stash_created" = true ]; then
        print_info "Restoring stashed changes..."
        if git stash pop; then
            print_success "Stashed changes restored"
        else
            print_warning "Could not automatically restore stashed changes (conflicts may exist)"
            print_info "Run 'git stash list' to see your stashes"
        fi
    fi
}

# Function to sync using merge
sync_merge() {
    print_info "Using merge strategy..."
    
    # Stash any uncommitted changes
    local stash_created=false
    if ! git diff --quiet HEAD; then
        print_warning "Uncommitted changes detected. Stashing..."
        if [ "$DRY_RUN" = false ]; then
            git stash push -m "Auto-stash before sync $(date +%Y%m%d-%H%M%S)"
            stash_created=true
        else
            print_info "[DRY-RUN] Would stash uncommitted changes"
        fi
    fi
    
    # Create backup
    local backup_branch
    backup_branch=$(create_backup)
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would merge upstream/$UPSTREAM_BRANCH into $LOCAL_BRANCH"
        if [ "$stash_created" = true ]; then
            print_info "[DRY-RUN] Would pop stashed changes"
        fi
        return
    fi
    
    # Perform merge
    print_info "Merging upstream/$UPSTREAM_BRANCH..."
    if git merge upstream/$UPSTREAM_BRANCH --no-ff -m "Merge upstream changes from 666ghj/MiroFish"; then
        print_success "Merge completed successfully!"
    else
        print_error "Merge has conflicts. Please resolve them manually."
        echo ""
        echo "Conflict resolution steps:"
        echo "  1. Resolve conflicts in the affected files"
        echo "  2. Run: git add <resolved-files>"
        echo "  3. Run: git commit"
        echo "  4. If you want to abort: git merge --abort"
        echo ""
        echo "Your original branch is backed up as: $backup_branch"
        exit 1
    fi
    
    # Pop stash if created
    if [ "$stash_created" = true ]; then
        print_info "Restoring stashed changes..."
        if git stash pop; then
            print_success "Stashed changes restored"
        else
            print_warning "Could not automatically restore stashed changes (conflicts may exist)"
            print_info "Run 'git stash list' to see your stashes"
        fi
    fi
}

# Function to push changes
push_changes() {
    print_info "Changes are ready to push to origin"
    read -p "Do you want to push to origin/$LOCAL_BRANCH now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ "$DRY_RUN" = false ]; then
            git push origin "$LOCAL_BRANCH"
            print_success "Changes pushed to origin/$LOCAL_BRANCH"
        else
            print_info "[DRY-RUN] Would push to origin/$LOCAL_BRANCH"
        fi
    else
        print_info "You can push later with: git push origin $LOCAL_BRANCH"
    fi
}

# Main execution
main() {
    echo "========================================"
    echo "  MiroFish Fork Sync Tool"
    echo "========================================"
    echo ""
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not a git repository. Please run this script from your MiroFish directory."
        exit 1
    fi
    
    # Check current branch
    local current_branch
    current_branch=$(git branch --show-current)
    print_info "Current branch: $current_branch"
    
    if [ "$current_branch" != "$LOCAL_BRANCH" ]; then
        print_warning "You are not on the $LOCAL_BRANCH branch."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Switch to $LOCAL_BRANCH branch first: git checkout $LOCAL_BRANCH"
            exit 0
        fi
    fi
    
    # Run sync steps
    check_upstream_remote
    fetch_upstream
    show_commit_summary
    
    echo ""
    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN MODE - No changes will be made"
    fi
    
    echo ""
    read -p "Continue with sync using $STRATEGY strategy? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Sync cancelled"
        exit 0
    fi
    
    # Perform sync based on strategy
    case $STRATEGY in
        rebase)
            sync_rebase
            ;;
        merge)
            sync_merge
            ;;
    esac
    
    echo ""
    print_success "Sync completed!"
    
    if [ "$DRY_RUN" = false ]; then
        push_changes
    fi
    
    echo ""
    print_info "Next steps:"
    echo "  - Review the changes"
    echo "  - Test your application"
    echo "  - Resolve any remaining issues"
    echo ""
    print_info "If you encounter issues, you can restore from the backup branch"
}

# Run main function
main "$@"
