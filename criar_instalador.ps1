$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$compilerCandidates = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
)
$compiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $compiler) {
    throw 'Inno Setup 6 não encontrado. Instale o Inno Setup antes de gerar o instalador.'
}

$output = Join-Path $root 'Instalador'
$work = Join-Path ([System.IO.Path]::GetTempPath()) ('AutoClickerPro-build-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work -ErrorAction Stop | Out-Null
try {
    & python -m PyInstaller --noconfirm --windowed --onedir --name AutoClickerPro `
        --distpath (Join-Path $work 'dist') --workpath (Join-Path $work 'build') `
        --specpath $work (Join-Path $root 'autoclicker.py')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar o executável com PyInstaller.' }

    New-Item -ItemType Directory -Path $output -Force | Out-Null
    & $compiler "/DAppSource=$(Join-Path $work 'dist\AutoClickerPro')" `
        "/DInstallerOutput=$output" (Join-Path $root 'instalador.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o instalador com Inno Setup.' }
    Write-Output "Instalador criado: $(Join-Path $output 'AutoClickerPro-Instalador.exe')"
}
finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction Stop
}
