# 本机做题进度监听 —— 透过隧道每 8 秒刷新各做题节点进度。
# 用法(本机 PowerShell): D:\code-bench-v2\watch_exam.ps1
# 前提: 你那条隧道开着 (ssh -N -L 2222:172.16.108.241:29001 cubestudio@172.16.108.241)
$key = "$HOME\.ssh\id_rsa"
$remote = "source /mnt/yangh559/bench/env_profile.sh >/dev/null 2>&1; python3 /mnt/yangh559/code-bench-v2/run/exam_monitor.py"
while ($true) {
  Clear-Host
  Write-Host "======== 做题/判卷实时进度  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ========" -ForegroundColor Cyan
  ssh -i $key -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p 2222 root@127.0.0.1 $remote
  Write-Host "`n(每 8 秒刷新 · Ctrl-C 退出)" -ForegroundColor DarkGray
  Start-Sleep -Seconds 8
}
