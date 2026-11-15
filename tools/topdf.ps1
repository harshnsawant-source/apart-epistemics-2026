param($in,$out)
$w = New-Object -ComObject Word.Application
$w.Visible = $false
try {
  $d = $w.Documents.Open($in, $false, $true)
  $d.ExportAsFixedFormat($out, 17)
  "pages: " + $d.ComputeStatistics(2)
  $d.Close($false)
} finally { $w.Quit() }
