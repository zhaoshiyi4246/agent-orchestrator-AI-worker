[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    $output = & $script:GitCommand @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git $($Arguments -join ' ')"
    }
    return @($output)
}

function Get-RelativeReleasePath {
    param([string]$Root, [string]$Path)
    $rootUri = [uri]($Root.TrimEnd("\") + "\")
    $pathUri = [uri]$Path
    return [uri]::UnescapeDataString(
        $rootUri.MakeRelativeUri($pathUri).ToString()).Replace("\", "/")
}

try {
    $script:GitCommand = (Get-Command "git" -ErrorAction SilentlyContinue).Source
    if (-not $script:GitCommand) {
        throw "Git executable was not found on PATH."
    }

    $repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
    $inside = Invoke-Git -Arguments @("-C", $repoRoot, "rev-parse",
                                      "--is-inside-work-tree")
    if (($inside -join "").Trim().ToLowerInvariant() -ne "true") {
        throw "build-release.ps1 is not inside a Git repository."
    }
    $dirty = Invoke-Git -Arguments @("-C", $repoRoot, "status",
                                     "--porcelain", "--untracked-files=all")
    if (@($dirty).Count -ne 0) {
        throw "Git working tree is not clean; commit or remove changes first."
    }

    $manifestPath = Join-Path $PSScriptRoot "release-manifest.txt"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Release manifest is missing."
    }
    $entries = @(
        Get-Content -LiteralPath $manifestPath -Encoding UTF8 |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ -and -not $_.StartsWith("#") }
    )
    if ($entries.Count -eq 0) {
        throw "Release manifest has no entries."
    }
    $seenEntries = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::Ordinal)
    foreach ($entry in $entries) {
        $parts = $entry.Split("/", [StringSplitOptions]::RemoveEmptyEntries)
        if ($entry -match '^[A-Za-z]:' -or $entry.StartsWith("/") -or
                $entry.StartsWith("\") -or $entry.Contains("\") -or
                $parts -contains "." -or $parts -contains "..") {
            throw "Illegal release manifest path: $entry"
        }
        if (-not $seenEntries.Add($entry)) {
            throw "Duplicate release manifest entry: $entry"
        }
    }

    $commitOutput = Invoke-Git -Arguments @("-C", $repoRoot, "rev-parse",
                                             "HEAD")
    $commit = ($commitOutput -join "").Trim()
    if ($commit -notmatch '^[0-9a-f]{40}$') {
        throw "Could not resolve the source commit."
    }
    $tracked = @(Invoke-Git -Arguments @(
        "-c", "core.quotepath=false", "-C", $repoRoot, "ls-tree", "-r",
        "--name-only", $commit))
    $trackedSet = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::Ordinal)
    foreach ($path in $tracked) {
        [void]$trackedSet.Add($path)
    }

    $expectedSet = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::Ordinal)
    foreach ($entry in $entries) {
        if ($entry.EndsWith("/")) {
            $matches = @($tracked | Where-Object {
                $_.StartsWith($entry, [StringComparison]::Ordinal)
            })
            if ($matches.Count -eq 0) {
                throw "Manifest directory has no tracked files at HEAD: $entry"
            }
            foreach ($match in $matches) {
                [void]$expectedSet.Add($match)
            }
        }
        else {
            if (-not $trackedSet.Contains($entry)) {
                throw "Manifest file is not tracked at HEAD: $entry"
            }
            [void]$expectedSet.Add($entry)
        }
    }
    [string[]]$expected = @($expectedSet)
    [Array]::Sort($expected, [StringComparer]::Ordinal)

    $outputRoot = [IO.Path]::GetFullPath($OutputDirectory)
    $repoPrefix = $repoRoot.TrimEnd("\") + "\"
    if ($outputRoot.Equals($repoRoot, [StringComparison]::OrdinalIgnoreCase) -or
            $outputRoot.StartsWith($repoPrefix,
                [StringComparison]::OrdinalIgnoreCase)) {
        throw "OutputDirectory must be outside the source repository."
    }
    if (Test-Path -LiteralPath $outputRoot) {
        throw "OutputDirectory already exists; choose a new empty path."
    }
    New-Item -ItemType Directory -Path $outputRoot | Out-Null
    $releaseRoot = Join-Path $outputRoot "release"
    $sourceArchive = Join-Path $outputRoot "source-from-head.zip"

    $archiveArgs = @("-C", $repoRoot, "archive", "--format=zip",
                     "--output=$sourceArchive", $commit, "--") + $expected
    & $script:GitCommand @archiveArgs
    if ($LASTEXITCODE -ne 0 -or
            -not (Test-Path -LiteralPath $sourceArchive -PathType Leaf)) {
        throw "git archive failed."
    }
    Expand-Archive -LiteralPath $sourceArchive -DestinationPath $releaseRoot
    Remove-Item -LiteralPath $sourceArchive -Force

    [string[]]$staged = @(
        Get-ChildItem -LiteralPath $releaseRoot -Recurse -File |
            ForEach-Object { Get-RelativeReleasePath $releaseRoot $_.FullName }
    )
    [Array]::Sort($staged, [StringComparer]::Ordinal)
    if ($staged.Count -ne $expected.Count -or
            (Compare-Object -ReferenceObject $expected -DifferenceObject $staged -CaseSensitive)) {
        throw "Staged file set does not match the manifest expansion."
    }

    $forbiddenNames = @(
        ".venv", "runtime", "__pycache__", ".pytest_cache", "clao-src",
        "ao-supervision-sidecar", "closed-loop-demo",
        "closed-loop-demo-origin.git")
    foreach ($relative in $staged) {
        $segments = $relative.Split("/")
        $leaf = $segments[-1]
        if (@($segments | Where-Object { $_ -in $forbiddenNames }).Count -gt 0 -or
                $leaf -like "*.pyc" -or $leaf -like "*.db-wal" -or
                $leaf -like "*.db-shm" -or $leaf -eq "state.db" -or
                $leaf -eq "bus_traffic.jsonl" -or
                $leaf -like "mission-panel-*.json" -or
                $leaf -like "codex-last-message*" -or
                $leaf -like "*.log") {
            throw "Generated or historical content reached staging: $relative"
        }
    }

    $missingLinks = @()
    foreach ($markdown in (Get-ChildItem -LiteralPath $releaseRoot -Recurse -File -Filter "*.md")) {
        $text = Get-Content -LiteralPath $markdown.FullName -Raw -Encoding UTF8
        foreach ($match in [regex]::Matches($text, '\[[^\]]+\]\(([^)]+)\)')) {
            $target = $match.Groups[1].Value.Split("#")[0]
            if (-not $target -or $target -match '^(https?://|mailto:)') {
                continue
            }
            $candidate = Join-Path $markdown.DirectoryName `
                ([uri]::UnescapeDataString($target))
            if (-not (Test-Path -LiteralPath $candidate)) {
                $missingLinks += (Get-RelativeReleasePath $releaseRoot `
                    $markdown.FullName)
            }
        }
    }
    if ($missingLinks.Count -ne 0) {
        throw "Release Markdown contains missing local links."
    }

    $secretPatterns = @(
        '(?i)[A-Z]:\\Users\\',
        '(?i)E:\\桌面\\',
        '(?i)sk-[A-Za-z0-9_-]{20,}',
        '(?i)gh[pousr]_[A-Za-z0-9]{20,}',
        '(?i)Authorization\s*:\s*Bearer\s+[A-Za-z0-9._~-]{20,}',
        '(?i)(OPENAI_API_KEY|ANTHROPIC_API_KEY)\s*[:=]\s*["'']?[A-Za-z0-9_-]{16,}'
    )
    foreach ($relative in $staged) {
        $file = Join-Path $releaseRoot $relative.Replace("/", "\")
        try {
            $text = Get-Content -LiteralPath $file -Raw -Encoding UTF8
        }
        catch {
            continue
        }
        foreach ($pattern in $secretPatterns) {
            if ($text -match $pattern) {
                throw "Potential credential or developer path in release: $relative"
            }
        }
    }

    $hashLines = [Collections.Generic.List[string]]::new()
    foreach ($relative in $staged) {
        $file = Join-Path $releaseRoot $relative.Replace("/", "\")
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        $hashLines.Add($hash.ToLowerInvariant() + "  " + $relative)
    }
    $hashFile = Join-Path $releaseRoot "SHA256SUMS.txt"
    [IO.File]::WriteAllLines(
        $hashFile, $hashLines, [Text.UTF8Encoding]::new($false))
    if (-not (Test-Path -LiteralPath $hashFile -PathType Leaf)) {
        throw "Failed to generate SHA256SUMS.txt."
    }

    $zipName = "closed-loop-v2-$($commit.Substring(0, 12)).zip"
    $zipPath = Join-Path $outputRoot $zipName
    Compress-Archive -LiteralPath $releaseRoot -DestinationPath $zipPath
    if (-not (Test-Path -LiteralPath $zipPath -PathType Leaf)) {
        throw "Failed to generate the release zip."
    }

    Write-Output "SOURCE_COMMIT=$commit"
    Write-Output "MANIFEST_FILES=$($expected.Count)"
    Write-Output "MARKDOWN_MISSING=0"
    Write-Output "SECRET_FINDINGS=0"
    Write-Output "SHA256SUMS=SHA256SUMS.txt"
    Write-Output "RELEASE_ZIP=$zipName"
    exit 0
}
catch {
    Write-Error ("Release build failed: " + $_.Exception.Message)
    exit 1
}
