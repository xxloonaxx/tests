$ErrorActionPreference = "Stop"

$projectPath = Join-Path $PSScriptRoot "YoutubeDownloader.csproj"

Write-Host "Publishing Win-x64 self-contained single-file package..."

$arguments = @(
    "publish",
    $projectPath,
    "-c", "Release",
    "/p:PublishProfile=Win-x64"
)

dotnet @arguments
