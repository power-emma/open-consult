param([string]$Port = "COM4", [string]$Log, [switch]$Spaced, [string]$Id = "EF")
$ecu = [Convert]::ToByte($Id, 16); $want = [byte](-bnot $ecu -band 0xFF)
$sw = [Diagnostics.Stopwatch]::StartNew()
function L($tag, $txt) { $line = "{0,10:F6} {1} {2}" -f $sw.Elapsed.TotalSeconds, $tag, $txt; Add-Content -Path $Log -Value $line -Encoding utf8; Write-Host $line }
function Hex($b) { ($b | ForEach-Object { $_.ToString("x2") }) -join " " }
$p = New-Object System.IO.Ports.SerialPort $Port, 9600, ([System.IO.Ports.Parity]::None), 8, ([System.IO.Ports.StopBits]::One)
$p.DtrEnable = $false; $p.RtsEnable = $false; $p.ReadTimeout = 200
try { $p.Open() } catch { Write-Error "cannot open ${Port}: $($_.Exception.InnerException.Message) (close ECUTalk?)"; exit 1 }
L "##" "open $Port (System.IO.Ports, DTR/RTS off) at $(Get-Date -Format s)"
function Rx($ms) {
  $got = New-Object System.Collections.Generic.List[byte]; $end = $sw.ElapsedMilliseconds + $ms
  while ($sw.ElapsedMilliseconds -lt $end) {
    if ($p.BytesToRead -gt 0) { $n = $p.BytesToRead; $buf = New-Object byte[] $n; $r = $p.Read($buf, 0, $n); $chunk = $buf[0..($r-1)]; L "RX" (Hex $chunk); $got.AddRange([byte[]]$chunk) } else { Start-Sleep -Milliseconds 5 }
  }
  return ,$got
}
function Tx([byte[]]$b) { L "TX" (Hex $b); $p.Write($b, 0, $b.Length) }
$ok = $false
for ($i = 1; $i -le 5 -and -not $ok; $i++) {
  L "##" "attempt $i"
  Tx @(0x30); [void](Rx 500)
  $p.DiscardInBuffer()
  if ($Spaced) { Tx @(0xFF); Start-Sleep -Milliseconds 280; Tx @(0xFF); Start-Sleep -Milliseconds 70; Tx @($ecu) } else { Tx @(0xFF, 0xFF, $ecu) }
  $g = Rx 2000
  if ($g.Contains($want)) { $ok = $true; L "##" "init ok id=$Id attempt=$i" }
}
if ($ok) {
  L "##" "D0 part number"
  Tx @(0xD0); [void](Rx 300); Tx @(0xF0); $d = Rx 800; Tx @(0x30); [void](Rx 500)
  $i0 = $d.IndexOf([byte]0xFF)
  if ($i0 -ge 0 -and $d.Count -gt $i0 + 1) { $n = [int]$d[$i0 + 1];$f = $d.GetRange($i0 + 2, [Math]::Min($n, $d.Count - $i0 - 2)).ToArray()
    L "##" ("D0 frame len={0} data: {1}" -f $n, (Hex $f))
    if ($f.Length -ge 22) { L "##" ("part number (openconsult decoding): {0:X2}{1:X2} 23710-{2:X}{3:X2}{4:X2}" -f $f[2], $f[3], $f[19], $f[20], $f[21]) }
    L "##" ("ASCII: " + (($f | % { if ($_ -ge 32 -and $_ -lt 127) { [char]$_ } else { '.' } }) -join '')) }
} else { L "##" ("init FAILED: no 0x{0:X2}" -f $want) }
$p.Close(); L "##" "close"
