# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"
  config.vm.box_check_update = false

  # Ortak VMware Workstation ayarları (Headless, hafif kaynak tüketimi)
  config.vm.provider "vmware_desktop" do |v|
    v.gui = false
    v.memory = 768
    v.cpus = 1
    v.vmx["memsize"] = "768"
    v.vmx["numvcpus"] = "1"
  end

  # Alternatif VirtualBox desteği (gerekirse)
  config.vm.provider "virtualbox" do |vb|
    vb.gui = false
    vb.memory = 768
    vb.cpus = 1
  end

  # 1. VM: GATEWAY (PIP + PDP + PEP Karar ve Yürütme Noktası)
  # Hem Alt Ağ A (192.168.50.2) hem Alt Ağ B (192.168.60.2) üzerinde arayüzü var (.1 VMware host adaptörüyle çakışmaması için .2 kullanıyoruz)
  config.vm.define "gateway" do |gw|
    gw.vm.hostname = "gateway"
    gw.vm.network "private_network", ip: "192.168.50.2", netmask: "255.255.255.0"
    gw.vm.network "private_network", ip: "192.168.60.2", netmask: "255.255.255.0"
    gw.vm.provision "shell", path: "setup/gateway_setup.sh"
  end

  # 2. VM: SERVER (Hedef Kurumsal Sunucu - Alt Ağ B: 192.168.60.20)
  # 192.168.50.0/24 ağına dönüş rotası gateway (192.168.60.1) üzerindendir
  config.vm.define "server" do |srv|
    srv.vm.hostname = "server"
    srv.vm.network "private_network", ip: "192.168.60.20", netmask: "255.255.255.0"
    srv.vm.provision "shell", path: "setup/server_setup.sh"
  end

  # 3. VM: CLIENT (İstemci / BYOD / Saldırgan - Alt Ağ A: 192.168.50.10)
  # 192.168.60.0/24 ağına gidiş rotası gateway (192.168.50.1) üzerindendir
  config.vm.define "client" do |cli|
    cli.vm.hostname = "client"
    cli.vm.network "private_network", ip: "192.168.50.10", netmask: "255.255.255.0"
    cli.vm.provision "shell", path: "setup/client_setup.sh"
  end
end
