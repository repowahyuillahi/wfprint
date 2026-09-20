# scripts/install_server.ps1 — idempoten. Jalankan sebagai admin (butuh untuk firewall).
param([string]$Exe = "python $PSScriptRoot/../wfprint.py --server --bind 192.168.1.10 --port 9100",
      [int]$Port = 9100,
      [string]$Subnet = "192.168.1.0/24")
$rule = Get-NetFirewallRule -DisplayName "wfprint $Port" -ErrorAction SilentlyContinue
if ($rule) { Remove-NetFirewallRule -DisplayName "wfprint $Port" }
New-NetFirewallRule -DisplayName "wfprint $Port" -Direction Inbound -Protocol TCP -LocalPort $Port -RemoteAddress $Subnet -Action Allow
$runPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
if (Get-ItemProperty -Path $runPath -Name "wfprint" -ErrorAction SilentlyContinue) {
  Set-ItemProperty -Path $runPath -Name "wfprint" -Value $Exe
} else {
  New-ItemProperty -Path $runPath -Name "wfprint" -Value $Exe -PropertyType String
}
Write-Host "OK: firewall LAN ($Subnet) + autostart terpasang. Jalankan: $Exe"
