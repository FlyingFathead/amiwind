# SPDX-License-Identifier: GPL-3.0-only
# Keep all build options in Python; forward each argument without evaluating it.
$ErrorActionPreference = 'Stop'
$buildArgs = @($args)
$toolsDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'amiwind-tools'
for ($i = 0; $i -lt $buildArgs.Count; $i++) {
    if ($buildArgs[$i] -eq '--tools-dir' -and $i + 1 -lt $buildArgs.Count) {
        $toolsDir = $buildArgs[$i + 1]
    } elseif ($buildArgs[$i] -like '--tools-dir=*') {
        $toolsDir = $buildArgs[$i].Substring('--tools-dir='.Length)
    }
}
$pythonArgs = @()
$python = $env:AMIWIND_PYTHON
if (-not $python) {
    foreach ($candidate in @((Join-Path $toolsDir 'venv\Scripts\python.exe'),
                             (Join-Path $toolsDir 'python\python.exe'))) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $python = $candidate
            break
        }
    }
}
if (-not $python) {
    $launcher = Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($launcher) {
        $python = $launcher.Source
        $pythonArgs = @('-3')
    } else {
        $command = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue
        if ($command) { $python = $command.Source }
    }
}
if (-not $python) {
    [Console]::Error.WriteLine('Windows CPython 3.10+ is required. Install Python or set AMIWIND_PYTHON to its python.exe. See docs/WINDOWS_BUILD.md.')
    exit 1
}
try {
    & $python @pythonArgs -B -u -X utf8 (Join-Path $PSScriptRoot 'tools\build_windows.py') @buildArgs
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
