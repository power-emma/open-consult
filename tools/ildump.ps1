param([string]$Exe, [string[]]$TypeNames)
$a = [Reflection.Assembly]::LoadFile($Exe)
$ops = @{}
foreach ($f in [Reflection.Emit.OpCodes].GetFields('Public,Static')) { $o = $f.GetValue($null); $ops[[uint16]([int]$o.Value -band 0xFFFF)] = $o }
function SB($x) { if ($x -gt 127) { $x - 256 } else { $x } }
$BF = [Reflection.BindingFlags]'Public,NonPublic,Instance,Static,DeclaredOnly'
function Tok($m, $tok) {
  try { $r = $m.Module.ResolveMember($tok, $m.DeclaringType.GetGenericArguments(), $null)
    if ($r -is [Reflection.MethodBase]) { return "$($r.DeclaringType.Name)::$($r.Name)(" + (($r.GetParameters() | % { $_.ParameterType.Name }) -join ',') + ")" }
    return "$($r.DeclaringType.Name)::$($r.Name)" } catch { return ("tok{0:x8}" -f $tok) }
}
foreach ($tn in $TypeNames) {
  $t = $a.GetType($tn)
  foreach ($m in @($t.GetConstructors($BF)) + @($t.GetMethods($BF))) {
    $body = $m.GetMethodBody(); if (-not $body) { continue }
    $il = $body.GetILAsByteArray()
    "==== $tn::$($m.Name)(" + (($m.GetParameters() | % { $_.ParameterType.Name }) -join ',') + ") -> $(if($m.ReturnType){$m.ReturnType.Name})"
    $i = 0
    while ($i -lt $il.Length) {
      $pos = $i; $v = [uint16]$il[$i]; $i++
      if ($v -eq 0xFE) { $v = [uint16](0xFE00 -bor $il[$i]); $i++ }
      $op = $ops[$v]; if (-not $op) { "  {0:x4}: ??{1:x}" -f $pos, $v; continue }
      $arg = ""
      switch ($op.OperandType.ToString()) {
        'InlineNone' {}
        'ShortInlineBrTarget' { $d = SB $il[$i]; $i++; $arg = "-> {0:x4}" -f ($i + $d) }
        'ShortInlineI' { $arg = SB $il[$i]; $i++ }
        'ShortInlineVar' { $arg = $il[$i]; $i++ }
        'InlineVar' { $arg = [BitConverter]::ToUInt16($il, $i); $i += 2 }
        'InlineBrTarget' { $d = [BitConverter]::ToInt32($il, $i); $i += 4; $arg = "-> {0:x4}" -f ($i + $d) }
        'InlineI' { $arg = [BitConverter]::ToInt32($il, $i); $i += 4 }
        'InlineI8' { $arg = [BitConverter]::ToInt64($il, $i); $i += 8 }
        'ShortInlineR' { $arg = [BitConverter]::ToSingle($il, $i); $i += 4 }
        'InlineR' { $arg = [BitConverter]::ToDouble($il, $i); $i += 8 }
        'InlineString' { $tok = [BitConverter]::ToInt32($il, $i); $i += 4; $arg = '"' + $m.Module.ResolveString($tok) + '"' }
        'InlineSwitch' { $n = [BitConverter]::ToInt32($il, $i); $i += 4 + 4 * $n; $arg = "switch($n)" }
        'InlineSig' { $i += 4 }
        default { $tok = [BitConverter]::ToInt32($il, $i); $i += 4; $arg = Tok $m $tok }
      }
      "  {0:x4}: {1} {2}" -f $pos, $op.Name, $arg
    }
  }
}
