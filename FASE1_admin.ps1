# Ejecutar en PowerShell como Administrador. Copiar y pegar bloque por bloque.

dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

winget install Docker.DockerDesktop
winget install Microsoft.VisualStudioCode

# FASE 6 - regla de firewall para acceso desde movil (opcional, tambien admin)
netsh advfirewall firewall add rule name="SpeakWise Dev" dir=in action=allow protocol=TCP localport=8000

# Cuando termines lo anterior, reinicia manualmente cuando te venga bien:
#   shutdown /r /t 30
#
# Después del reinicio, en PowerShell normal (sin admin):
#   wsl --update
#   wsl --set-default-version 2
#
# Luego abre Docker Desktop desde el menu inicio y espera a que
# el icono de la ballena quede verde (no animado), 2-3 minutos.
