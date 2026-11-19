# Tüm Deney Senaryolarını (Senaryo 1, 2 ve 3) Otomatik Koşturan Orkestrasyon Betiği
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host "=== [0/4] Hedef Sunucu Servislerinin Kontrolü ===" -ForegroundColor Cyan
vagrant ssh server -c "sudo ip route replace 192.168.50.0/24 via 192.168.60.2; sudo systemctl restart target-services.service"
vagrant ssh client -c "sudo ip route replace 192.168.60.0/24 via 192.168.50.2"
vagrant ssh gateway -c "sudo sysctl -w net.ipv4.ip_forward=1"

Write-Host "=== [1/4] Senaryo 1A: Statik Erişim Kontrolü (Baseline) Koşturuluyor (45 sn) ===" -ForegroundColor Yellow
$gwJob1 = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    vagrant ssh gateway -c "sudo python3 /vagrant/gateway_engine/controller_daemon.py --mode static --duration 46 --output /vagrant/results/scenario1_gateway_static.csv"
} -ArgumentList $PSScriptRoot
Start-Sleep -Seconds 2
vagrant ssh client -c "python3 /vagrant/experiments/client_traffic_runner.py --scenario 1 --mode static"
Wait-Job $gwJob1 | Out-Null
Remove-Job $gwJob1

Write-Host "=== [2/4] Senaryo 1B: Uyarlanabilir (Adaptive) Erişim Kontrolü Koşturuluyor (45 sn) ===" -ForegroundColor Green
$gwJob2 = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    vagrant ssh gateway -c "sudo python3 /vagrant/gateway_engine/controller_daemon.py --mode adaptive --duration 46 --output /vagrant/results/scenario1_gateway_adaptive.csv"
} -ArgumentList $PSScriptRoot
Start-Sleep -Seconds 2
vagrant ssh client -c "python3 /vagrant/experiments/client_traffic_runner.py --scenario 1 --mode adaptive"
Wait-Job $gwJob2 | Out-Null
Remove-Job $gwJob2

Write-Host "=== [3/4] Senaryo 2: Bağlam Duyarlı 4 Kademeli Kısıtlama Testi Koşturuluyor (42 sn) ===" -ForegroundColor Magenta
$gwJob3 = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    vagrant ssh gateway -c "sudo python3 /vagrant/gateway_engine/controller_daemon.py --mode adaptive --duration 44 --output /vagrant/results/scenario2_gateway.csv"
} -ArgumentList $PSScriptRoot
Start-Sleep -Seconds 2
vagrant ssh client -c "python3 /vagrant/experiments/client_traffic_runner.py --scenario 2"
Wait-Job $gwJob3 | Out-Null
Remove-Job $gwJob3

Write-Host "=== [4/4] Senaryo 3: Performans Gecikmesi (RTT/PDP) ve False-Positive Testi Koşturuluyor ===" -ForegroundColor Cyan
$gwJob4 = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    vagrant ssh gateway -c "sudo python3 /vagrant/gateway_engine/controller_daemon.py --mode adaptive --duration 12 --output /vagrant/results/scenario3_gateway.csv"
} -ArgumentList $PSScriptRoot
Start-Sleep -Seconds 2
vagrant ssh client -c "python3 /vagrant/experiments/client_traffic_runner.py --scenario 3"
Wait-Job $gwJob4 | Out-Null
Remove-Job $gwJob4

Write-Host "=== Grafikler Üretiliyor ===" -ForegroundColor Green
python "$PSScriptRoot\experiments\plot_results.py"
Write-Host "=== TÜM DENEYLER TAMAMLANDI ===" -ForegroundColor Green
