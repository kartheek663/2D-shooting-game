param(
    [string]$RemoteUrl = 'https://github.com/kartheek663/2D-shooting-game.git'
)

# Simple script to initialize, commit and push this folder to a remote GitHub repo.
# Run in PowerShell in the project folder.

Write-Host "Checking for git..."
try {
    git --version | Out-Null
} catch {
    Write-Error "Git not found. Install Git for Windows: https://git-scm.com/download/win"
    exit 1
}

if (-not (Test-Path .git)) {
    Write-Host "Initializing new git repository..."
    git init
} else {
    Write-Host "Repository already initialised."
}

# Stage changes
Write-Host "Adding files..."
git add .

# Commit
Write-Host "Committing..."
$commitMsg = Read-Host "Enter commit message (or press Enter for default)"
if ([string]::IsNullOrWhiteSpace($commitMsg)) { $commitMsg = "Add/update game files" }

git commit -m "$commitMsg" --allow-empty

# Configure remote
# If remote origin already exists, ask whether to update it
$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $existing) {
    Write-Host "Existing remote 'origin' set to: $existing"
    $ans = Read-Host "Replace remote origin with $RemoteUrl? (y/N)"
    if ($ans -match '^[Yy]') {
        git remote remove origin
        git remote add origin $RemoteUrl
    }
} else {
    Write-Host "Adding remote origin: $RemoteUrl"
    git remote add origin $RemoteUrl
}

# Ensure main branch
Write-Host "Ensuring branch 'main'"
git branch -M main

Write-Host "Pushing to remote... You may be prompted for credentials (use PAT if you have 2FA)."
try {
    git push -u origin main
    Write-Host "Push complete."
} catch {
    Write-Error "Push failed. If you see authentication errors, try one of these options:`n- Use a Personal Access Token (PAT) for HTTPS authentication when prompted for a password.`n- Set up SSH keys and use the SSH remote URL: git@github.com:username/repo.git`n- Install and use Git Credential Manager or GitHub CLI (gh) to authenticate.`n"
    exit 1
}
