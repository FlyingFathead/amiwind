# SPDX-License-Identifier: GPL-3.0-only
[CmdletBinding()]
param(
    [string]$ToolsDir = (Join-Path (Split-Path $PSScriptRoot -Parent) 'amiwind-tools'),
    [switch]$Plan,
    [switch]$Yes,
    [switch]$Offline
)
$ErrorActionPreference = 'Stop'
try {
    $ToolsDir = [IO.Path]::GetFullPath($ToolsDir)
    $repo = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
    if ($ToolsDir -eq $repo -or $ToolsDir.StartsWith($repo + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Keep dependency tools outside the source checkout, for example C:\AmiWind\amiwind-tools.'
    }
    # MSYS2 documents short ASCII paths without whitespace as its supported layout.
    if ($ToolsDir -notmatch '^[A-Za-z]:\\[A-Za-z0-9_.\\-]+$') {
        throw 'Use a local ASCII tools path without spaces or shell metacharacters.'
    }
    $spec = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'config\windows-toolchain.json') | ConvertFrom-Json
    Write-Output "AmiWind Windows tools: $ToolsDir"
    foreach ($name in @('python','msys2','sdk','ericw','ffmpeg')) {
        Write-Output ("{0} {1}: {2}" -f $name,$spec.$name.version,$spec.$name.url)
    }
    Write-Output ('Python constraints: ' + ($spec.python_constraints -join ', '))
    Write-Output ('MSYS2: ' + $spec.msys2_package_policy)
    Write-Output 'QCC uses the same pinned source revision and file hashes as Linux.'
    if ($Plan -or -not $Yes) {
        Write-Output 'Preview only. Run setup-windows.cmd -Yes to install, or -Yes -Offline to reuse the cache and provisioned MSYS2.'
        exit 0
    }
    $downloads = Join-Path $ToolsDir 'downloads'
    New-Item -ItemType Directory -Path $downloads -Force | Out-Null
    function Get-VerifiedInstaller($item) {
        $target = Join-Path $downloads $item.filename
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
            if ($Offline) { throw "Offline installer missing: $target" }
            $partial = $target + '.partial'
            & "$env:SystemRoot\System32\curl.exe" --fail --location --proto '=https' --proto-redir '=https' --connect-timeout 20 --max-time 600 --output $partial $item.url
            if ($LASTEXITCODE -ne 0) { throw "Download failed: $($item.url)" }
            if ((Get-Item -LiteralPath $partial).Length -ne $item.bytes -or (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) {
                throw "Installer checksum/size mismatch: $partial"
            }
            Move-Item -LiteralPath $partial -Destination $target
        }
        if ((Get-Item -LiteralPath $target).Length -ne $item.bytes -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) {
            throw "Cached installer checksum/size mismatch: $target"
        }
        return $target
    }
    function Install-Local($installer, $arguments, $label) {
        Write-Output "Installing $label (silent; a Windows approval prompt may appear)."
        $process = Start-Process -FilePath $installer -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
        if ($process.ExitCode -notin @(0,3010)) { throw "$label installer exited $($process.ExitCode)" }
        if ($process.ExitCode -eq 3010) { throw "$label requests a Windows restart. Restart, then rerun setup." }
    }
    # Keep installer caches even on a reuse run, so the offline prerequisites are explicit.
    $pythonInstaller = Get-VerifiedInstaller $spec.python
    $msysInstaller = Get-VerifiedInstaller $spec.msys2
    $sdkInstaller = Get-VerifiedInstaller $spec.sdk
    $python = Join-Path $ToolsDir 'python\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        if (Test-Path -LiteralPath (Join-Path $ToolsDir 'python')) { throw 'Incomplete Python directory; inspect it before retrying.' }
        # SHA-256 remains available offline; online also checks Windows trust/signature.
        if (-not $Offline) {
            $signature = Get-AuthenticodeSignature -LiteralPath $pythonInstaller
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Python Software Foundation') {
                throw 'Python Software Foundation signature validation failed.'
            }
        }
        Install-Local $pythonInstaller @('/quiet','InstallAllUsers=0',"TargetDir=$ToolsDir\python",'Include_launcher=0','Include_test=0','Include_doc=0','Include_pip=1','Include_tcltk=0','PrependPath=0','Shortcuts=0','AssociateFiles=0','/log',"$downloads\python-install.log") 'Python'
    }
    $version = & $python -c 'import platform; print(platform.python_version())'
    if ($LASTEXITCODE -ne 0) { throw 'Managed Python could not run.' }
    if ([version]$version -lt [version]'3.10') { throw 'AmiWind requires Python 3.10 or later.' }
    if ($version -ne $spec.python.version) {
        Write-Warning "Using Python $version; the Windows setup default is $($spec.python.version). The original Linux reference is compared after setup. Package compatibility will be checked."
    }
    if (-not (Test-Path -LiteralPath "$ToolsDir\msys64\usr\bin\bash.exe")) {
        if ($Offline) { throw 'Offline setup requires an already provisioned MSYS2 tree (including package cache). Run online setup once first.' }
        if (Test-Path -LiteralPath "$ToolsDir\msys64") { throw 'Incomplete MSYS2 directory; inspect before retrying.' }
        Install-Local $msysInstaller @('in','--confirm-command','--accept-messages','--root',"$ToolsDir\msys64") 'MSYS2'
    }
    if (-not (Test-Path -LiteralPath "$ToolsDir\sdk\bin\m68k-amigaos-gcc.exe")) {
        if (Test-Path -LiteralPath "$ToolsDir\sdk") { throw 'Incomplete SDK directory; inspect before retrying.' }
        Install-Local $sdkInstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',"/DIR=$ToolsDir\sdk",'/NOICONS',"/LOG=$downloads\sdk-install.log") 'Amiga SDK'
    }
    $setupArgs = @('--tools-dir', $ToolsDir)
    if ($Offline) { $setupArgs += '--offline' }
    & $python -B -u -X utf8 (Join-Path $PSScriptRoot 'tools\setup_windows.py') @setupArgs
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine('Windows setup: ' + $_.Exception.Message)
    exit 1
}
