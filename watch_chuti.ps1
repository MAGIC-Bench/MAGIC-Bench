# 本机【出题(生成)】进度监听 —— 透过隧道每 10 秒刷新。用法(本机 PowerShell): D:\code-bench-v2\watch_chuti.ps1
# 前提: 隧道开着 (ssh -N -L 2222:172.16.108.241:29001 cubestudio@172.16.108.241)
$key = "$HOME\.ssh\id_rsa"
$remote = "source /mnt/yangh559/bench/env_profile.sh >/dev/null 2>&1; python3 /mnt/yangh559/code-bench-v2/run/chuti_monitor.py"
while ($true) {
  Clear-Host
  Write-Host "======== 出题(生成)实时进度  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ========" -ForegroundColor Cyan
  ssh -i $key -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p 2222 root@127.0.0.1 $remote
  Write-Host "`n(每 10 秒刷新 · Ctrl-C 退出)" -ForegroundColor DarkGray
  Start-Sleep -Seconds 10
}
