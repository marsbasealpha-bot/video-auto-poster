# Create the analyzer inbox and analyzed output folders
$InboxFolder   = "D:\Video Auto-Poster\analyzer_inbox"
$AnalyzedFolder = "D:\Video Auto-Poster\analyzed"

foreach ($folder in @($InboxFolder, $AnalyzedFolder)) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        Write-Host "Created: $folder" -ForegroundColor Green
    } else {
        Write-Host "Already exists: $folder" -ForegroundColor Yellow
    }
}
Write-Host "`nAnalyzer folders ready!" -ForegroundColor Cyan
