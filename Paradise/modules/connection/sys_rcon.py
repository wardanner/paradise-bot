#? <- Implementa la comunicación directa con el servidor de Zomboid via protocolo Source RCON.
import os
import asyncio
import struct
from dotenv import load_dotenv

# Source RCON Protocol Packet Types
SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0

load_dotenv()

async def send_rcon_command(command_str: str) -> str:
    """
    Envía un comando RCON conectándose directamente por Sockets TCP asíncronos
    usando el protocolo nativo Source RCON.
    """
    ip = os.getenv("IP_ADDRESS")
    port = os.getenv("RCON_PORT")
    password = os.getenv("RCON_PASSWORD")  
    
    if not ip or not port or not password:
        return "Error crítico: Variables de entorno IP/PT/PS no configuradas."

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, int(port)), timeout=5.0
        )
        
        def make_packet(req_id: int, req_type: int, body: str) -> bytes:
            body_bytes = body.encode('utf-8') + b'\x00\x00'
            size = 10 + len(body_bytes) - 2
            return struct.pack('<iii', size, req_id, req_type) + body_bytes
            
        async def read_packet():
            size_data = await asyncio.wait_for(reader.readexactly(4), timeout=5.0)
            size = struct.unpack('<i', size_data)[0]
            packet_data = await asyncio.wait_for(reader.readexactly(size), timeout=5.0)
            res_id, res_type = struct.unpack('<ii', packet_data[:8])
            body = packet_data[8:-2].decode('utf-8', errors='ignore')
            return res_id, res_type, body

        # 1. Login
        auth_packet = make_packet(1, SERVERDATA_AUTH, password)
        writer.write(auth_packet)
        await writer.drain()
        
        # El servidor normalmente devuelve un paquete RESPONSE_VALUE en blanco seguido del AUTH_RESPONSE
        res_id, res_type, body = await read_packet()
        if res_type == SERVERDATA_RESPONSE_VALUE:
             res_id, res_type, body = await read_packet()
             
        if res_id == -1 or res_type != SERVERDATA_AUTH_RESPONSE:
            writer.close()
            await writer.wait_closed()
            return "Error RCON: Autenticación fallida o contraseña incorrecta."
            
        # 2. Enviar Comando
        cmd_packet = make_packet(2, SERVERDATA_EXECCOMMAND, command_str)
        writer.write(cmd_packet)
        await writer.drain()
        
        # 3. Leer Respuesta
        res_id, res_type, response_body = await read_packet()
        
        # Cerrar conexión
        writer.close()
        await writer.wait_closed()
        
        return response_body.strip()
    except asyncio.TimeoutError:
        return "Error RCON: Tiempo de espera agotado al conectar o leer respuesta."
    except Exception as e:
        return f"Error ejecutando RCON: {e}"

async def run_flag_commands(flag_code: str, args_dict: dict = None) -> list:
    """
    Lee las directrices de una flag desde flags.json y ejecuta 
    el comando principal seguido de sus comandos adicionales
    (command_2, command_3, etc.), reemplazando las variables.
    
    Retorna una lista de tuplas: [(comando_enviado, respuesta_del_server), ...]
    """
    if args_dict is None:
        args_dict = {}
        
    results = []
    
            
    return results
