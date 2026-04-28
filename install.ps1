[CmdletBinding()]
param(
    [switch]$ApplyExplorerPatcher,
    [switch]$EnableAutoStart,
    [switch]$SetInterlude87Wallpaper,
    [switch]$BackupCurrentConfigs,
    [switch]$SetAccentColor
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[DinoThemes] $Message"
}

function Get-RepoRoot {
    return Split-Path -Parent $PSCommandPath
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Copy-IfExists {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (Test-Path -LiteralPath $Source) {
        $parent = Split-Path -Parent $Destination
        Ensure-Directory -Path $parent
        Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
        return $true
    }

    return $false
}

function Backup-CurrentConfigs {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupRoot = Join-Path $env:USERPROFILE "Documents\DinoThemes_Backups\$timestamp"
    Ensure-Directory -Path $backupRoot

    Write-Step "Creating backup at $backupRoot"

    $copied = 0
    $copied += [int](Copy-IfExists -Source (Join-Path $env:APPDATA "ExplorerPatcher") -Destination (Join-Path $backupRoot "ExplorerPatcher"))
    $copied += [int](Copy-IfExists -Source (Join-Path $env:LOCALAPPDATA "Packages\Microsoft.PowerToys_8wekyb3d8bbwe\LocalState") -Destination (Join-Path $backupRoot "PowerToys"))
    $copied += [int](Copy-IfExists -Source (Join-Path $env:APPDATA "Rainmeter") -Destination (Join-Path $backupRoot "Rainmeter"))
    $copied += [int](Copy-IfExists -Source (Join-Path $env:APPDATA "RoundedTB") -Destination (Join-Path $backupRoot "RoundedTB"))
    $copied += [int](Copy-IfExists -Source (Join-Path $env:APPDATA "TranslucentTB") -Destination (Join-Path $backupRoot "TranslucentTB"))
    $copied += [int](Copy-IfExists -Source (Join-Path $env:APPDATA "AutoHotkey") -Destination (Join-Path $backupRoot "AutoHotkey"))
    $copied += [int](Copy-IfExists -Source (Join-Path $env:LOCALAPPDATA "Packages\FilesCommunity.Files_1y0xx7n9077q4\LocalState") -Destination (Join-Path $backupRoot "FilesApp"))

    Write-Step "Backup complete ($copied locations copied)"
}

function Apply-ExplorerPatcherProfile {
    $repoRoot = Get-RepoRoot
    $epDir = Join-Path $repoRoot "ExplorerPatcher"

    if (-not (Test-Path -LiteralPath $epDir)) {
        Write-Step "ExplorerPatcher folder missing, skipping profile import"
        return
    }

    $latest = Get-ChildItem -LiteralPath $epDir -Filter "Dinos_Patcher_V*.reg" -File |
        Sort-Object Name -Descending |
        Select-Object -First 1

    if (-not $latest) {
        Write-Step "No ExplorerPatcher profile found, skipping"
        return
    }

    Write-Step "Importing ExplorerPatcher profile: $($latest.Name)"
    & reg.exe import "$($latest.FullName)" | Out-Null
    Write-Step "ExplorerPatcher profile imported"
}

function Enable-AutoStartScript {
    $repoRoot = Get-RepoRoot
    $scriptPath = Join-Path $repoRoot "AutoKey\workspaces.ahk"

    if (-not (Test-Path -LiteralPath $scriptPath)) {
        Write-Step "workspaces.ahk not found, skipping autostart"
        return
    }

    $startup = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startup "DinoThemes Workspaces.lnk"

    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $scriptPath
    $shortcut.WorkingDirectory = Split-Path -Parent $scriptPath
    $shortcut.Description = "Dino Themes workspace hotkeys"
    $shortcut.Save()

    Write-Step "Autostart shortcut created: $shortcutPath"
}

function Set-Interlude87Wallpaper {
    $repoRoot = Get-RepoRoot
    $wall = Join-Path $repoRoot "Walls\02222026104754_interlude_87.png"

    if (-not (Test-Path -LiteralPath $wall)) {
        Write-Step "interlude_87 wallpaper not found, skipping wallpaper update"
        return
    }

    $picturesWalls = Join-Path $env:USERPROFILE "Pictures\DinoThemes\Walls"
    Ensure-Directory -Path $picturesWalls
    $targetWall = Join-Path $picturesWalls "02222026104754_interlude_87.png"
    Copy-Item -LiteralPath $wall -Destination $targetWall -Force

    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name Wallpaper -Value $targetWall
    Start-Process -FilePath "rundll32.exe" -ArgumentList "user32.dll,UpdatePerUserSystemParameters" -WindowStyle Hidden -Wait

    Write-Step "Wallpaper set to interlude_87"
}

function Set-AccentColorDino {
    # DWM expects color bytes in ABGR order. 50,67,50 -> 0x00324332
    $accentDword = 0x00324332
    New-Item -Path "HKCU:\Software\Microsoft\Windows\DWM" -Force | Out-Null
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\DWM" -Name AccentColor -Type DWord -Value $accentDword
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\DWM" -Name ColorPrevalence -Type DWord -Value 1
    Write-Step "Accent color set to RGB(50,67,50)"
}

try {
    Write-Step "Starting theme setup"

    if ($BackupCurrentConfigs) {
        Backup-CurrentConfigs
    }

    if ($ApplyExplorerPatcher) {
        Apply-ExplorerPatcherProfile
    }

    if ($EnableAutoStart) {
        Enable-AutoStartScript
    }

    if ($SetInterlude87Wallpaper) {
        Set-Interlude87Wallpaper
    }

    if ($SetAccentColor) {
        Set-AccentColorDino
    }

    Write-Step "Theme setup complete"
    exit 0
}
catch {
    Write-Error "Theme setup failed: $($_.Exception.Message)"
    exit 1
}
