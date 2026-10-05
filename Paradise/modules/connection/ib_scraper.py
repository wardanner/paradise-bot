#? <- Realiza web scraping en el panel de control de Indifferent Broccoli para gestionar el estado del servidor.
import os
import requests
from bs4 import BeautifulSoup
import time

LOGIN_URL = "https://dashboard.indifferentbroccoli.com/login"
DASHBOARD_URL = "https://dashboard.indifferentbroccoli.com/"

def perform_action_sync(action: str):
    """
    Versión síncrona de web scraping vía requests puro, sin navegadores.
    action: 'start', 'stop', 'restart', 'status'
    """
    email = os.getenv("IB_EMAIL")
    password = os.getenv("IB_PASSWORD")
    ftp_user = os.getenv("FTP_USERNAME")  # Usado como ID del servidor
    
    if not email or not password or not ftp_user:
        return False, "Faltan credenciales IB_EMAIL, IB_PASSWORD o FTP_USERNAME en .env"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    })

    # 1. Login
    login_data = {"email": email, "password": password}
    try:
        res_login = session.post(LOGIN_URL, data=login_data, allow_redirects=False, timeout=10)
        if res_login.status_code != 302 and "dashboard" not in res_login.url:
            return False, "\u001b[2;31m Error: Falla de autenticación en Indifferent Broccoli.\u001b[0m"
    except Exception as e:
        return False, f"\u001b[2;31m Error conectando a IB (Login):\u001b[0m \u001b[1;31m{e}\u001b[0m"

    # 2. Consultar Dashboard para obtener el estado actual
    try:
        res_dash = session.get(DASHBOARD_URL, timeout=10)
        soup = BeautifulSoup(res_dash.text, "html.parser")
    except Exception as e:
        return False, f"\u001b[2;31m Error cargando el dashboard:\u001b[0m \u001b[1;31m{e}\u001b[0m"
    
    # 3. Analizar estado
    is_restarting = False
    is_online = False
    is_offline = False

    # Buscar el botón start-stop para el id de nuestro servidor
    btn = soup.find(id=f"start-stop-{ftp_user}")
    
    if btn:
        btn_text = btn.text.lower().strip()
        is_restarting = False # 'restart' is a different button, 'restarting' state hides start/stop
        is_online = "stop" in btn_text
        is_offline = "start" in btn_text
    else:
        # Si no vemos el botón Start/Stop normal, podría estar reiniciando/cargando
        # Buscamos la etiqueta de status "Server status"
        status_badges = soup.find_all("li")
        for badge in status_badges:
            if "Server status" in badge.text:
                mono = badge.find(class_="font-mono")
                if mono:
                    txt = mono.text.lower().strip()
                    if "restarting" in txt or "starting" in txt:
                        is_restarting = True
                        break

    # Resolver acción local status
    if action == "status":
        if is_online:
            return True, "\u001b[2;34m El servidor está \u001b[0m\u001b[1;32mONLINE\u001b[0m"
        elif is_offline:
            return True, "\u001b[2;34m El servidor está \u001b[2;40m\u001b[2;31m\u001b[1;31mOFFLINE\u001b[0m\u001b[2;31m\u001b[2;40m\u001b[0m\u001b[2;34m\u001b[2;40m\u001b[0m\u001b[2;34m\u001b[0m"
        else:
            return True, "\u001b[2;34m El servidor está \u001b[0m\u001b[1;33mREINICIANDO/INICIANDO...\u001b[0m"

    # Condiciones previas
    if action == "start":
        if is_online:
            return False, "\u001b[2;34m El servidor ya estaba \u001b[0m\u001b[1;32mONLINE\u001b[0m"
    elif action == "stop":
        if is_offline:
            return False, "\u001b[2;34m El servidor ya estaba \u001b[2;40m\u001b[2;31m\u001b[1;31mOFFLINE\u001b[0m\u001b[2;31m\u001b[2;40m\u001b[0m\u001b[2;34m\u001b[2;40m\u001b[0m\u001b[2;34m\u001b[0m"

    # 4. Ejecutar la acción contra la API oculta
    target_url = f"https://dashboard.indifferentbroccoli.com/{action}"
    action_data = {"serverLinuxUsername": ftp_user}
    
    try:
        res_action = session.post(target_url, data=action_data, timeout=10)
        # El servidor responde con JSON indicando "notificationHtml" o éxito
        if res_action.status_code == 200:
            return True, f"\u001b[2;34m Comando \u001b[0m\u001b[1;2m'{action}'\u001b[0m\u001b[2;34m enviado correctamente.\u001b[0m"
        else:
            return False, f"\u001b[2;31m Error inesperado del panel (HTTP {res_action.status_code})\u001b[0m"
    except Exception as e:
        return False, f"\u001b[2;31m Error POSTeando la acción:\u001b[0m \u001b[1;31m{e}\u001b[0m"

async def perform_action(action: str):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, perform_action_sync, action)

