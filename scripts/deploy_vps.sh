#!/usr/bin/env bash
# ==============================================================================
# Meme Hunter - Script de Aprovisionamiento y Despliegue en VPS (Ubuntu 22.04/24.04)
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo "🛡️  Iniciando aprovisionamiento seguro de VPS para Meme Hunter"
echo "=========================================================="

# 1. Actualización de paquetes
echo "[1/6] Actualizando paquetes del sistema..."
apt-get update -qq && apt-get upgrade -y -qq

# 2. Instalación de dependencias base y Docker
echo "[2/6] Instalando Docker y herramientas esenciales..."
apt-get install -y -qq \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    fail2ban \
    ufw \
    git \
    htop

# Agregar repositorio oficial de Docker si no existe
if ! command -v docker &> /dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

systemctl enable docker
systemctl start docker

# 3. Configuración de Seguridad y Firewall (UFW)
echo "[3/6] Configurando cortafuegos UFW y Fail2ban..."
ufw default deny incoming
ufw default allow outgoing
ufw limit 22/tcp comment 'SSH con limitador de fuerza bruta'
# IMPORTANTE: NO exponemos el puerto 8080 al mundo; se accede vía Túnel SSH
ufw --force enable

systemctl enable fail2ban
systemctl restart fail2ban

# 4. Estructura de Directorios
echo "[4/6] Creando directorios operativos en /opt/meme_hunter..."
mkdir -p /opt/meme_hunter/user_data/logs
mkdir -p /opt/meme_hunter/user_data/data
mkdir -p /opt/meme_hunter/scripts

# 5. Permisos de Usuario
echo "[5/6] Verificando permisos de Docker..."
if [ -n "${SUDO_USER:-}" ]; then
    usermod -aG docker "$SUDO_USER"
fi

echo "=========================================================="
echo "✅ VPS Aprovisionado con éxito"
echo "=========================================================="
echo ""
echo "Pasos siguientes para el despliegue:"
echo "1. Clona el repositorio o transfiere los archivos a: /opt/meme_hunter"
echo "2. Crea el archivo .env con tus secretos (Binance / Telegram)"
echo "3. Levanta el bot en segundo plano:"
echo "   cd /opt/meme_hunter && docker compose -f docker-compose.live.yml up -d"
echo ""
echo "Para acceder a FreqUI de forma 100% segura desde tu PC:"
echo "   ssh -L 8080:127.0.0.1:8080 <usuario>@<IP_DEL_VPS>"
echo "   Luego abre en tu navegador: http://localhost:8080"
echo "=========================================================="
