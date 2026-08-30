# -*- coding: utf-8 -*-
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ext import voice_recv
import os
import sys
import shutil
import subprocess
import wave
import asyncio
import aiohttp
import itertools
import json
import re
import socket
import time
import unicodedata
import csv
import random
import sqlite3
from array import array
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from groq import Groq
import google.generativeai as genai
from rcon.exceptions import EmptyResponse, SessionTimeout, WrongPassword
from rcon.source.proto import Packet, Type

# --- 1. CARREGAR SEGREDOS E CAMINHOS ---
print("--- INICIANDO ZOMBOIDOS V148 (RCON TEIMOSO COM TENTATIVAS MÚLTIPLAS) 🛡  ---")
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# =========================================================
# CONFIGURAÇÃO DO MAMALIO + STATUS
# =========================================================
RCON_IP = os.getenv("RCON_HOST", "127.0.0.1") 
RCON_PORT = int(os.getenv("RCON_PORT", 27015))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
CANAL_STATUS_ID = os.getenv("CANAL_STATUS_ID")
RCON_CONNECT_TIMEOUT = float(os.getenv("RCON_CONNECT_TIMEOUT", "6"))
RCON_COMMAND_TIMEOUT = float(os.getenv("RCON_COMMAND_TIMEOUT", "12"))
RCON_MAX_TENTATIVAS = max(1, int(os.getenv("RCON_MAX_TENTATIVAS", "4")))
RCON_RETRY_DELAY = float(os.getenv("RCON_RETRY_DELAY", "1.5"))
RCON_FALHAS_OFFLINE = max(2, int(os.getenv("RCON_FALHAS_OFFLINE", "4")))
RCON_SESSION_TTL = float(os.getenv("RCON_SESSION_TTL", "90"))
RCON_RECENT_SUCCESS_WINDOW = float(os.getenv("RCON_RECENT_SUCCESS_WINDOW", "180"))
MEMORIA_IA_TTL = max(300, int(os.getenv("MEMORIA_IA_TTL", "21600")))
MAX_CANAIS_MEMORIA_IA = max(10, int(os.getenv("MAX_CANAIS_MEMORIA_IA", "100")))
MAX_MENSAGENS_MEMORIA_IA = max(3, int(os.getenv("MAX_MENSAGENS_MEMORIA_IA", "9")))
MAX_DURACAO_REUNIAO_SEGUNDOS = max(60, int(os.getenv("MAX_DURACAO_REUNIAO_SEGUNDOS", "900")))
# =========================================================

FRIENDHOST_CACHE_CONTAINER = "/home/container/.cache"
FRIENDHOST_CACHE_VOLUME_LEGADO = "/var/lib/pterodactyl/volumes/87611b15-879c-4b7b-a2b5-bf2f5628344f/.cache"

def escolher_cache_friendhost_padrao():
    """Usa o caminho visivel pelo processo do bot.

    No Pterodactyl/FriendHost o bot roda dentro do container e enxerga os
    arquivos em /home/container/.cache. O caminho /var/lib/pterodactyl/... e
    valido apenas para processos que rodam no host fisico, fora do container.
    """
    for caminho in (FRIENDHOST_CACHE_CONTAINER, FRIENDHOST_CACHE_VOLUME_LEGADO):
        if os.path.isdir(caminho):
            return caminho
    # Se o cache ainda nao existe no boot, mantenha o caminho padrao do
    # container: o mod o cria assim que o servidor inicia.
    return FRIENDHOST_CACHE_CONTAINER

PZ_CACHE_BASE_PADRAO = escolher_cache_friendhost_padrao()
FRIENDHOST_CSV_BASE_PADRAO = os.path.join(PZ_CACHE_BASE_PADRAO, "Lua", "FriendHost_Data")
FRIENDHOST_LOGS_BASE_PADRAO = os.path.join(PZ_CACHE_BASE_PADRAO, "Logs")
PZ_SAVE_BASE_PADRAO = os.path.join(PZ_CACHE_BASE_PADRAO, "Saves", "Multiplayer", "OrganicRP")
PZ_DB_BASE_PADRAO = os.path.join(PZ_CACHE_BASE_PADRAO, "db")
CSV_BASE_PATH = os.getenv("CSV_BASE_PATH", FRIENDHOST_CSV_BASE_PADRAO)
LOGS_PATH = os.getenv("LOGS_PATH", FRIENDHOST_LOGS_BASE_PADRAO)
TXT_BASE_PATH = os.getenv("TXT_BASE_PATH", LOGS_PATH)
PLAYERS_DB_PATH = os.getenv("PLAYERS_DB_PATH", os.path.join(PZ_SAVE_BASE_PADRAO, "players.db"))
WHITELIST_DB_PATH = os.getenv("WHITELIST_DB_PATH", os.path.join(PZ_DB_BASE_PADRAO, "OrganicRP.db"))
# Build 42.20 do PZ so permite ao Lua gravar em extensoes de texto aprovadas, entao
# o FriendHost passou a escrever "*.csv.txt". O conteudo continua CSV com ';'.
# Os nomes legados ficam como fallback para servidor que ainda use o mod antigo.
CAMINHO_MORTES = os.getenv("CAMINHO_MOD_MORTES", os.path.join(CSV_BASE_PATH, "Servidor", "deaths.csv.txt"))
CAMINHO_EVENTOS = os.getenv("CAMINHO_MOD_EVENTOS", os.path.join(CSV_BASE_PATH, "Servidor", "event_history.csv.txt"))
CAMINHO_PLAYERS_ONLINE = os.getenv("CAMINHO_MOD_PLAYERS_ONLINE", os.path.join(CSV_BASE_PATH, "Servidor", "online_players.txt"))

NOMES_ARQUIVO_MORTES = ("deaths.csv.txt", "deaths.csv")
NOMES_ARQUIVO_EVENTOS = ("event_history.csv.txt", "event_history.csv")
# ZomboidOSOnlinePlayersCSV (B42.20) grava um username por linha em
# online_players.txt. Os CSVs anteriores continuam como fallback para quem
# ainda estiver no mod legado.
NOMES_ARQUIVO_ONLINE = (
    "online_players.txt",
    "players_online.csv.txt", "players_online.csv",
    "online_players.csv.txt", "online_players.csv",
)
CANAL_MORTES_ID = os.getenv("CANAL_MORTES_ID")
CANAL_EVENTOS_ID = os.getenv("CANAL_EVENTOS_ID")
CANAL_VIDAS_ID = os.getenv("CANAL_VIDAS_ID")
NOME_CALL_INGAME = os.getenv("NOME_CALL_INGAME", "in-game")
# Alem da call in-game, estas sao calls oficiais que tambem mantem o jogador
# regular. O nome da call in-game sempre entra na lista, mesmo se o .env mudar.
CANAIS_CALL_PERMITIDAS_RAW = os.getenv(
    "CANAIS_CALL_PERMITIDAS",
    "Sala de espera,Atendimento 1,Atendimento 2,Atendimento 3,TRABALHANDO",
)
TEMPO_GRACA_CALL_INGAME = max(30, int(os.getenv("TEMPO_GRACA_CALL_INGAME", "30")))
INTERVALO_MONITOR_CALL_INGAME = max(10, int(os.getenv("INTERVALO_MONITOR_CALL_INGAME", "20")))
COOLDOWN_TENTATIVA_CALL_INGAME = max(20, int(os.getenv("COOLDOWN_TENTATIVA_CALL_INGAME", "60")))
TOLERANCIA_SUMICO_CALL_INGAME = max(30, int(os.getenv("TOLERANCIA_SUMICO_CALL_INGAME", "60")))
# Um valor vazio no .env nao deve desligar sem querer a protecao do Thiago.
USUARIO_PROTEGIDO_CALL_ID = (
    os.getenv("USUARIO_PROTEGIDO_CALL_ID", "").strip() or "500259309251198986"
)
ATRASO_RETORNO_CALL_PROTEGIDA = 5
MENSAGEM_KICK_CALL_INGAME = os.getenv(
    "MENSAGEM_KICK_CALL_INGAME",
    "Voce foi desconectado por NAO estar em uma call permitida do Discord. "
    "Entre na call in-game, Sala de espera, Atendimento ou TRABALHANDO e conecte novamente.",
)
# Cargos do jogo que nunca sao expulsos. Normalizados na hora do uso, porque
# normalizar_chave_personagem so existe mais abaixo no arquivo.
CARGOS_JOGO_ISENTOS_CALL_RAW = os.getenv(
    "CARGOS_ISENTOS_CALL", "admin,moderator,moderador,overseer,gm,observer"
)

CHAVES_GEMINI = [os.getenv("GEMINI_API_KEY_1"), os.getenv("GEMINI_API_KEY_2"), os.getenv("GEMINI_API_KEY_3")]
CHAVES_GEMINI = [chave for chave in CHAVES_GEMINI if chave]

if not DISCORD_TOKEN or not GROQ_API_KEY or not CHAVES_GEMINI:
    print(" ERRO: Faltam chaves no arquivo .env!")
    exit()

roleta_gemini = itertools.cycle(CHAVES_GEMINI)
client_groq = Groq(api_key=GROQ_API_KEY)

# --- 2. BANCOS DE DADOS ---
CARGOS_PERMITIDOS = ["DONO DO SERVIDOR", "ADMINISTRADOR", "STAFF", "SUPORTE", "FOUNDER"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARQUIVO_AUDIO = os.path.join(BASE_DIR, "reuniao_zomboid.wav")
ARQUIVO_VIPS = os.path.join(BASE_DIR, "vips.json")
ARQUIVO_PAINEIS = os.path.join(BASE_DIR, "paineis.json")
ARQUIVO_STATUS = os.path.join(BASE_DIR, "status_jogadores.json")
ARQUIVO_PENDENTES = os.path.join(BASE_DIR, "fichas_pendentes.json")
ARQUIVO_MSG_STATUS = os.path.join(BASE_DIR, "msg_status_id.json") 
ARQUIVO_SORTEIOS = os.path.join(BASE_DIR, "sorteios.json")
ARQUIVO_PERSONAGENS = os.path.join(BASE_DIR, "personagens.json")
ARQUIVO_HISTORICO_PERSONAGENS = os.path.join(BASE_DIR, "historico_personagens.json")
ARQUIVO_REGISTROS_PERSONAGENS = os.path.join(BASE_DIR, "registros_personagens.json")
ARQUIVO_TEMPLATES = os.path.join(BASE_DIR, "templates_mensagens.json")
ARQUIVO_FICHAS_EM_ANALISE = os.path.join(BASE_DIR, "fichas_em_analise.json")
ARQUIVO_CONFIG_VIDAS = os.path.join(BASE_DIR, "config_vidas.json")
ARQUIVO_VERSAO_BOT = os.path.join(BASE_DIR, "versao_bot.json")
ARQUIVO_CONFIG_ABERTURA = os.path.join(BASE_DIR, "config_abertura.json")
ARQUIVO_CONFIG_TICKETS = os.path.join(BASE_DIR, "config_tickets.json")
ARQUIVO_TICKETS_FECHAMENTO = os.path.join(BASE_DIR, "tickets_fechamento.json")

MINUTOS_FECHAR_TICKET_PADRAO = 5

# Fuso usado para interpretar/mostrar horarios digitados pela staff.
# -3 = horario de Brasilia. A host pode rodar em UTC, entao nao da para confiar
# no relogio local do servidor.
FUSO_BOT_HORAS = float(os.getenv("FUSO_HORARIO", "-3"))
PASTA_BACKUP_UPDATE = os.path.join(BASE_DIR, "backup_update")

# --- AUTO-ATUALIZACAO PELO GITHUB ---
# O repositorio e FIXO de proposito. Se viesse por parametro do comando,
# qualquer admin poderia mandar o bot baixar e executar codigo de outro lugar.
REPO_GITHUB = os.getenv("REPO_GITHUB", "Th14goAlvex/bot-organic")
BRANCH_GITHUB = os.getenv("BRANCH_GITHUB", "main")

# Regra de ouro do updater: ele NUNCA toca em .json, .env ou qualquer dado.
# So codigo e dependencias sao substituidos.
EXTENSOES_ATUALIZAVEIS = (".py",)
ARQUIVOS_ATUALIZAVEIS_EXTRAS = ("requirements.txt",)
NUNCA_ATUALIZAR = (".json", ".env", ".db", ".wav", ".log", ".bak", ".tmp")

ESPERA_ANALISE_FICHA_SEGUNDOS = 180

memorias = {}
memorias_ultima_atividade = {}
gravadores = {}
servidor_online = True 
falhas_rcon = 0 
fila_pendentes_em_espera = False
tarefa_monitor_mortes = None
tarefa_monitor_eventos = None
tarefa_monitor_call_ingame = None
tarefa_varredura_fichas = None
tarefa_retomar_analises = None
tarefa_fichas_pendentes = None
varredura_fichas_executada = False
controle_call_ingame = {}
tarefas_retorno_call_protegida = {}
tarefas_remocao_vip = {}
tarefas_fichas = set()
tarefas_fichas_por_chave = {}
fichas_em_processamento = set()
# O recurso escasso e o RCON, nao a espera. Por isso o semaforo protege apenas
# o comando adduser: as analises de 3 minutos rodam todas em paralelo e a fila
# de abertura do servidor nao vira gargalo.
semaforo_rcon_registro = asyncio.Semaphore(3)

def _ler_json_arquivo(caminho):
    if not os.path.exists(caminho) or os.stat(caminho).st_size == 0:
        return None
    try:
        # utf-8-sig remove o BOM se existir (Bloco de Notas e PowerShell gravam
        # com BOM) e funciona normalmente em arquivo sem BOM.
        with open(caminho, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except UnicodeDecodeError:
        # Arquivos antigos podem ter sido gravados no encoding do Windows.
        with open(caminho, "r", encoding="cp1252") as f:
            return json.load(f)

def carregar_json_seguro(caminho, padrao):
    """Lê um banco JSON. Se o arquivo principal estiver corrompido (queda no meio
    da escrita, por exemplo), tenta recuperar a partir do backup .bak."""
    try:
        dados = _ler_json_arquivo(caminho)
        if dados is not None:
            return dados
    except Exception as erro:
        print(f"[DB] {os.path.basename(caminho)} ilegivel ({erro}); tentando backup .bak")
        try:
            dados = _ler_json_arquivo(caminho + ".bak")
            if dados is not None:
                print(f"[DB] {os.path.basename(caminho)} restaurado a partir do backup.")
                with suppress(Exception):
                    salvar_json_seguro(caminho, dados)
                return dados
        except Exception as erro_backup:
            print(f"[DB] Backup de {os.path.basename(caminho)} tambem falhou: {erro_backup}")

    return padrao() if callable(padrao) else padrao

def salvar_json_seguro(caminho, dados, ensure_ascii=True):
    """Grava o JSON de forma atomica: escreve num .tmp, força o flush no disco e
    só então substitui o arquivo real (os.replace e atomico no Windows e no Linux).
    O conteudo anterior fica guardado como .bak. Se a maquina cair no meio da
    gravacao, o banco antigo continua intacto."""
    caminho_tmp = caminho + ".tmp"
    try:
        with open(caminho_tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=ensure_ascii)
            f.flush()
            os.fsync(f.fileno())

        if os.path.exists(caminho) and os.stat(caminho).st_size > 0:
            with suppress(Exception):
                os.replace(caminho, caminho + ".bak")

        os.replace(caminho_tmp, caminho)
        return True
    except Exception as erro:
        print(f"[DB] FALHA ao salvar {os.path.basename(caminho)}: {erro}")
        with suppress(Exception):
            if os.path.exists(caminho_tmp):
                os.remove(caminho_tmp)
        return False

def carregar_vips():
    return carregar_json_seguro(ARQUIVO_VIPS, {})

def salvar_vips(dados):
    salvar_json_seguro(ARQUIVO_VIPS, dados)

def carregar_paineis():
    return carregar_json_seguro(ARQUIVO_PAINEIS, {})

def salvar_paineis(dados):
    salvar_json_seguro(ARQUIVO_PAINEIS, dados)

def carregar_status():
    return carregar_json_seguro(ARQUIVO_STATUS, {})

def salvar_status(dados):
    salvar_json_seguro(ARQUIVO_STATUS, dados)

def carregar_pendentes():
    return carregar_json_seguro(ARQUIVO_PENDENTES, [])

def salvar_pendentes(dados):
    salvar_json_seguro(ARQUIVO_PENDENTES, dados)

def carregar_fichas_em_analise():
    return carregar_json_seguro(ARQUIVO_FICHAS_EM_ANALISE, [])

def salvar_fichas_em_analise(dados):
    salvar_json_seguro(ARQUIVO_FICHAS_EM_ANALISE, dados)

def carregar_msg_status():
    try:
        dados = carregar_json_seguro(ARQUIVO_MSG_STATUS, {}) or {}
        msg_id = dados.get("msg_id")
        return int(msg_id) if msg_id else None
    except Exception: return None

def salvar_msg_status(msg_id):
    salvar_json_seguro(ARQUIVO_MSG_STATUS, {"msg_id": msg_id})

def ficha_ja_esta_pendente(pendentes, canal_id, msg_id):
    return any(p.get("canal_id") == canal_id and p.get("msg_id") == msg_id for p in pendentes)

# --- FILA DURAVEL DE REGISTRO ---
# Regra de ouro: uma ficha SO sai da fila quando o personagem estiver confirmado
# no servidor. Qualquer falha de conexao devolve a ficha para a fila em vez de
# descartar. E o que garante que, na abertura do servidor, ninguem fique de fora
# mesmo que o bot caia antes, durante ou depois.

ESTADO_AGUARDANDO_ABERTURA = "aguardando_abertura"
ESTADO_AGUARDANDO_STAFF = "aguardando_staff"
ESTADO_AGUARDANDO_SERVIDOR = "aguardando_servidor"
ESTADO_NA_FILA = "na_fila"
ESTADO_REGISTRANDO = "registrando"
MAX_TENTATIVAS_REGISTRO = 15

def normalizar_entrada_fila(p):
    """Aceita entradas do formato antigo ({canal_id, msg_id}) e completa os
    campos novos, para a fila que ja existe em disco continuar valendo."""
    agora = datetime.now().isoformat()
    return {
        "canal_id": p.get("canal_id"),
        "msg_id": p.get("msg_id"),
        "autor_id": p.get("autor_id"),
        "conteudo_ficha": p.get("conteudo_ficha"),
        "estado": p.get("estado") or ESTADO_AGUARDANDO_SERVIDOR,
        "rcon_enviado": bool(p.get("rcon_enviado", False)),
        "tentativas": int(p.get("tentativas") or 0),
        "criado_em": p.get("criado_em") or agora,
        "atualizado_em": p.get("atualizado_em") or agora,
        "ultimo_erro": p.get("ultimo_erro"),
        "alertou_staff": bool(p.get("alertou_staff", False)),
    }

def carregar_fila_registro():
    dados = carregar_pendentes()
    if not isinstance(dados, list):
        return []
    return [
        normalizar_entrada_fila(p) for p in dados
        if isinstance(p, dict) and p.get("canal_id") and p.get("msg_id")
    ]

def salvar_fila_registro(fila):
    salvar_pendentes(fila)

def buscar_na_fila(canal_id, msg_id, fila=None):
    fila = carregar_fila_registro() if fila is None else fila
    return next(
        (p for p in fila if p.get("canal_id") == canal_id and p.get("msg_id") == msg_id),
        None,
    )

def registrar_na_fila(message, estado, **campos):
    """Cria ou atualiza a entrada duravel da ficha."""
    fila = carregar_fila_registro()
    entrada = buscar_na_fila(message.channel.id, message.id, fila)

    if entrada is None:
        entrada = normalizar_entrada_fila({
            "canal_id": message.channel.id,
            "msg_id": message.id,
            "autor_id": message.author.id,
            "conteudo_ficha": message.content if getattr(message, "via_modal", False) else None,
        })
        fila.append(entrada)

    entrada["estado"] = estado
    entrada.update(campos)
    entrada["atualizado_em"] = datetime.now().isoformat()
    salvar_fila_registro(fila)
    return dict(entrada)

def atualizar_entrada_fila(canal_id, msg_id, **campos):
    fila = carregar_fila_registro()
    entrada = buscar_na_fila(canal_id, msg_id, fila)
    if entrada is None:
        return None

    entrada.update(campos)
    entrada["atualizado_em"] = datetime.now().isoformat()
    salvar_fila_registro(fila)
    return dict(entrada)

def remover_da_fila_registro(canal_id, msg_id):
    fila = carregar_fila_registro()
    restantes = [
        p for p in fila
        if not (p.get("canal_id") == canal_id and p.get("msg_id") == msg_id)
    ]
    if len(restantes) != len(fila):
        salvar_fila_registro(restantes)
        return True
    return False

def registrar_ficha_em_analise(message, msg_espera_id, fim_analise, bypass=False, checar_online=True):
    """Grava em disco que esta ficha esta no meio dos 3 minutos de analise.
    Se o bot cair agora, o on_ready retoma exatamente de onde parou."""
    analises = [
        a for a in carregar_fichas_em_analise()
        if not (a.get("canal_id") == message.channel.id and a.get("msg_id") == message.id)
    ]
    analises.append({
        "canal_id": message.channel.id,
        "msg_id": message.id,
        "guild_id": message.guild.id if message.guild else None,
        "autor_id": message.author.id,
        "msg_espera_id": msg_espera_id,
        "fim_analise": fim_analise.isoformat(),
        "bypass": bypass,
        "checar_online": checar_online,
        # Ficha vinda do Modal nao existe como mensagem no canal: o conteudo
        # precisa ficar guardado aqui para o bot conseguir retomar apos reiniciar.
        "conteudo_ficha": message.content if getattr(message, "via_modal", False) else None,
    })
    salvar_fichas_em_analise(analises)

async def reconstruir_ficha_salva(canal, registro):
    """Recria o alvo do processamento a partir de um registro em disco.
    Ficha do Modal vira um FichaSubmetida; ficha digitada volta a ser a
    mensagem original do jogador."""
    conteudo = registro.get("conteudo_ficha")
    if not conteudo:
        return await canal.fetch_message(registro.get("msg_id"))

    autor_id = registro.get("autor_id")
    autor = canal.guild.get_member(autor_id) if canal.guild else None
    if not autor and canal.guild:
        autor = await canal.guild.fetch_member(autor_id)
    if not autor:
        raise LookupError(f"Autor {autor_id} nao encontrado no servidor")

    return FichaSubmetida(conteudo, autor, canal, canal.guild, registro.get("msg_id"))

def remover_ficha_em_analise(canal_id, msg_id):
    analises = carregar_fichas_em_analise()
    restantes = [
        a for a in analises
        if not (a.get("canal_id") == canal_id and a.get("msg_id") == msg_id)
    ]
    if len(restantes) != len(analises):
        salvar_fichas_em_analise(restantes)

def resposta_rcon_indica_falha_cadastro(resposta):
    texto = (resposta or "").lower()
    padroes_falha = [
        "already exists",
        "user already",
        "username already",
        "error",
        "failed",
        "invalid",
        "usage:",
        "unknown command",
        "no such command",
        "exception",
    ]
    return any(padrao in texto for padrao in padroes_falha)

def carregar_sorteios():
    return carregar_json_seguro(ARQUIVO_SORTEIOS, {})

def salvar_sorteios(dados):
    salvar_json_seguro(ARQUIVO_SORTEIOS, dados)

def carregar_personagens():
    return carregar_json_seguro(ARQUIVO_PERSONAGENS, {})

def salvar_personagens(dados):
    salvar_json_seguro(ARQUIVO_PERSONAGENS, dados)

def carregar_historico_personagens():
    return carregar_json_seguro(ARQUIVO_HISTORICO_PERSONAGENS, {})

def salvar_historico_personagens(dados):
    salvar_json_seguro(ARQUIVO_HISTORICO_PERSONAGENS, dados, ensure_ascii=False)

def carregar_registros_personagens():
    return carregar_json_seguro(ARQUIVO_REGISTROS_PERSONAGENS, {})

def salvar_registros_personagens(dados):
    salvar_json_seguro(ARQUIVO_REGISTROS_PERSONAGENS, dados, ensure_ascii=False)

# --- SISTEMA DE VIDAS (limite de personagens por temporada) ---
# Guardamos VIDAS USADAS, nunca vidas restantes. E isso que faz o limite ser
# ajustavel sem resetar ninguem: se o limite sobe de 3 para 4, quem ja gastou 1
# passa de 2 para 3 restantes automaticamente, sem precisar mexer em nada.

CONFIG_VIDAS_PADRAO = {
    "ilimitado": True,
    "limite_vidas": 0,
    "vidas_usadas": {},
    "vidas_extras": {},
}

def carregar_config_vidas():
    config = carregar_json_seguro(ARQUIVO_CONFIG_VIDAS, {})
    if not isinstance(config, dict):
        config = {}

    resultado = dict(CONFIG_VIDAS_PADRAO)
    resultado.update(config)
    resultado["ilimitado"] = bool(resultado.get("ilimitado", True))
    resultado["limite_vidas"] = max(0, int(resultado.get("limite_vidas") or 0))
    for chave in ("vidas_usadas", "vidas_extras"):
        valor = resultado.get(chave)
        resultado[chave] = valor if isinstance(valor, dict) else {}
    return resultado

def salvar_config_vidas(config):
    salvar_json_seguro(ARQUIVO_CONFIG_VIDAS, config, ensure_ascii=False)

def vidas_usadas_jogador(user_id_str, config=None):
    """Quantas recriacoes o jogador ja fez. Se nao houver contador gravado,
    deduz do historico de personagens (o 1o personagem nao gasta vida)."""
    config = config or carregar_config_vidas()
    usadas = config.get("vidas_usadas", {})

    if user_id_str in usadas:
        with suppress(Exception):
            return max(0, int(usadas[user_id_str]))

    historico = carregar_historico_personagens().get(user_id_str) or []
    return max(0, len(historico) - 1)

def calcular_vidas(user_id_str):
    """Retorna a situacao de vidas do jogador.
    restantes = (limite da temporada + bonus manual) - vidas ja usadas"""
    user_id_str = str(user_id_str)
    config = carregar_config_vidas()
    usadas = vidas_usadas_jogador(user_id_str, config)

    if config["ilimitado"]:
        return {"ilimitado": True, "usadas": usadas, "extras": 0,
                "limite": 0, "total": 0, "restantes": None}

    extras = 0
    with suppress(Exception):
        extras = int(config["vidas_extras"].get(user_id_str, 0))

    total = max(0, config["limite_vidas"] + extras)
    return {
        "ilimitado": False,
        "usadas": usadas,
        "extras": extras,
        "limite": config["limite_vidas"],
        "total": total,
        "restantes": max(0, total - usadas),
    }

def consumir_vida(user_id_str):
    """Marca mais uma recriacao usada. Chamado so quando o registro foi
    confirmado no servidor."""
    user_id_str = str(user_id_str)
    config = carregar_config_vidas()
    config["vidas_usadas"][user_id_str] = vidas_usadas_jogador(user_id_str, config) + 1
    salvar_config_vidas(config)
    return calcular_vidas(user_id_str)

def adicionar_vidas_extras(user_id_str, quantidade):
    """Bonus manual da staff para um jogador especifico (aceita negativo)."""
    user_id_str = str(user_id_str)
    config = carregar_config_vidas()

    atual = 0
    with suppress(Exception):
        atual = int(config["vidas_extras"].get(user_id_str, 0))

    novo = atual + int(quantidade)
    if novo:
        config["vidas_extras"][user_id_str] = novo
    else:
        config["vidas_extras"].pop(user_id_str, None)

    salvar_config_vidas(config)
    return calcular_vidas(user_id_str)

def jogador_pode_criar_personagem(user_id_str, tem_personagem_atual):
    """O primeiro personagem da temporada nunca gasta vida e nunca e bloqueado."""
    if not tem_personagem_atual:
        return True, calcular_vidas(user_id_str)

    vidas = calcular_vidas(user_id_str)
    if vidas["ilimitado"]:
        return True, vidas
    return vidas["restantes"] > 0, vidas

def texto_vidas_restantes(vidas):
    if vidas["ilimitado"]:
        return "♾ **Vidas ilimitadas** nesta temporada."
    if vidas["restantes"] <= 0:
        return "💀 **Você não tem mais vidas.** Este foi seu último personagem da temporada."
    plural = "vida" if vidas["restantes"] == 1 else "vidas"
    return f"❤ Você ainda tem **{vidas['restantes']} {plural}** (personagens que ainda pode criar depois deste)."

# --- FECHAMENTO AUTOMATICO DOS TICKETS ---
# O prazo fica gravado em disco em vez de um sleep na memoria: assim o ticket
# nao vira orfao se o bot reiniciar no meio da espera.

def carregar_config_tickets():
    config = carregar_json_seguro(ARQUIVO_CONFIG_TICKETS, {})
    return config if isinstance(config, dict) else {}

def salvar_config_tickets(dados):
    salvar_json_seguro(ARQUIVO_CONFIG_TICKETS, dados, ensure_ascii=False)

def minutos_fechar_ticket():
    """Minutos ate o ticket de registro ser apagado, ou None se desativado."""
    config = carregar_config_tickets()
    if config.get("desativado"):
        return None
    try:
        minutos = int(config.get("minutos", MINUTOS_FECHAR_TICKET_PADRAO))
    except Exception:
        minutos = MINUTOS_FECHAR_TICKET_PADRAO
    return minutos if minutos > 0 else None

def carregar_tickets_para_fechar():
    dados = carregar_json_seguro(ARQUIVO_TICKETS_FECHAMENTO, [])
    return dados if isinstance(dados, list) else []

def salvar_tickets_para_fechar(dados):
    salvar_json_seguro(ARQUIVO_TICKETS_FECHAMENTO, dados)

def agendar_fechamento_ticket(canal_id, minutos):
    lista = [t for t in carregar_tickets_para_fechar() if t.get("canal_id") != canal_id]
    lista.append({"canal_id": canal_id, "fechar_em": time.time() + minutos * 60})
    salvar_tickets_para_fechar(lista)

def cancelar_fechamento_ticket(canal_id):
    lista = carregar_tickets_para_fechar()
    restantes = [t for t in lista if t.get("canal_id") != canal_id]
    if len(restantes) != len(lista):
        salvar_tickets_para_fechar(restantes)

# --- AGENDAMENTO DA ABERTURA DOS REGISTROS ---
# Permite abrir os tickets antes do servidor existir: as fichas entram na fila
# duravel e so sao aprovadas na data/hora marcada.

def carregar_config_abertura():
    config = carregar_json_seguro(ARQUIVO_CONFIG_ABERTURA, {})
    return config if isinstance(config, dict) else {}

def salvar_config_abertura(dados):
    salvar_json_seguro(ARQUIVO_CONFIG_ABERTURA, dados, ensure_ascii=False)

def agora_local():
    """Horario 'de Brasilia' (ou o fuso configurado), independente do relogio da host."""
    return datetime.now(timezone.utc) + timedelta(hours=FUSO_BOT_HORAS)

def epoch_de_horario_local(momento_local):
    """Converte um horario digitado pela staff (no fuso configurado) em epoch UTC."""
    return (momento_local.replace(tzinfo=timezone.utc) - timedelta(hours=FUSO_BOT_HORAS)).timestamp()

def aprovacao_automatica_ativa():
    """Quando desligada, a ficha e recebida e guardada, mas so vira personagem
    depois que a staff aprovar com /aprovar_ficha. Padrao: ligada."""
    config = carregar_config_abertura()
    return not bool(config.get("aprovacao_manual"))

def definir_aprovacao_automatica(ativa, autor):
    config = carregar_config_abertura()
    config["aprovacao_manual"] = not ativa
    config["aprovacao_alterada_em"] = datetime.now().isoformat()
    config["aprovacao_alterada_por"] = str(autor)
    salvar_config_abertura(config)

def timestamp_abertura_registros():
    """Epoch em que a aprovacao comeca, ou None se nao houver agendamento."""
    valor = carregar_config_abertura().get("abertura_epoch")
    try:
        return float(valor) if valor else None
    except Exception:
        return None

def registros_estao_liberados():
    momento = timestamp_abertura_registros()
    return momento is None or time.time() >= momento

def segundos_ate_abertura():
    momento = timestamp_abertura_registros()
    return 0 if momento is None else max(0, int(momento - time.time()))

def texto_abertura_discord(prefixo="A aprovação começa"):
    """Usa timestamp do Discord: cada pessoa ve no proprio fuso, sem confusao."""
    momento = timestamp_abertura_registros()
    if momento is None:
        return ""
    marca = int(momento)
    if time.time() >= momento:
        return "✅ **Os registros já estão abertos.**"
    return f"🗓 **{prefixo} <t:{marca}:F>** (<t:{marca}:R>)."

def interpretar_data_hora(texto_data, texto_hora):
    """Aceita data em 07/08/2026, 07-08-2026, 2026-08-07 ou 07/08,
    e hora em 20:00, 20h, 20h30, 20.
    Devolve (datetime_local_naive, erro)."""
    texto_hora = (texto_hora or "").strip().lower().replace("h", ":").strip(":")
    if not texto_hora:
        return None, "Informe a **hora** (ex: `20:00`)."

    partes = [p for p in re.split(r"[:\s.]+", texto_hora) if p]
    try:
        hora = int(partes[0])
        minuto = int(partes[1]) if len(partes) > 1 else 0
    except Exception:
        return None, f"Não entendi a hora `{texto_hora}`. Use algo como `20:00`."
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        return None, "Hora inválida. Use de `00:00` até `23:59`."

    referencia = agora_local().replace(tzinfo=None)
    texto_data = (texto_data or "").strip()

    if not texto_data:
        alvo = referencia.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        # Hora que ja passou hoje significa amanha.
        if alvo <= referencia:
            alvo += timedelta(days=1)
        return alvo, None

    numeros = [n for n in re.split(r"[/\-.\s]+", texto_data) if n.isdigit()]
    if len(numeros) < 2:
        return None, f"Não entendi a data `{texto_data}`. Use `DD/MM/AAAA`."

    try:
        if len(numeros[0]) == 4:                      # AAAA-MM-DD
            ano, mes, dia = int(numeros[0]), int(numeros[1]), int(numeros[2])
        else:                                          # DD/MM[/AAAA]
            dia, mes = int(numeros[0]), int(numeros[1])
            ano = int(numeros[2]) if len(numeros) > 2 else referencia.year
            if ano < 100:
                ano += 2000
        return datetime(ano, mes, dia, hora, minuto), None
    except ValueError as erro:
        return None, f"Data inválida: {erro}."

def carregar_versao_bot():
    return carregar_json_seguro(ARQUIVO_VERSAO_BOT, {}) or {}

def salvar_versao_bot(dados):
    salvar_json_seguro(ARQUIVO_VERSAO_BOT, dados, ensure_ascii=False)

def arquivo_e_atualizavel(caminho_repo):
    """Decide se um arquivo do repositorio pode ser sobrescrito na atualizacao.
    Dado do bot (json), segredo (.env) e banco NUNCA entram aqui."""
    nome = caminho_repo.lower()

    if nome.endswith(NUNCA_ATUALIZAR):
        return False
    if any(parte in nome for parte in ("/.", "\\.")) or nome.startswith("."):
        return False
    if nome.endswith(EXTENSOES_ATUALIZAVEIS):
        return True
    return os.path.basename(nome) in ARQUIVOS_ATUALIZAVEIS_EXTRAS

async def consultar_ultimo_commit():
    """Ultimo commit do repositorio. Devolve (dados, erro)."""
    url = f"https://api.github.com/repos/{REPO_GITHUB}/commits/{BRANCH_GITHUB}"
    cabecalhos = {"Accept": "application/vnd.github+json", "User-Agent": "OrganicRP-Bot"}
    try:
        tempo = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=tempo) as sessao:
            async with sessao.get(url, headers=cabecalhos) as resposta:
                if resposta.status == 404:
                    return None, f"Repositório `{REPO_GITHUB}` ou branch `{BRANCH_GITHUB}` não encontrado."
                if resposta.status == 403:
                    return None, "GitHub recusou (limite de requisições). Tente de novo em alguns minutos."
                if resposta.status != 200:
                    return None, f"GitHub respondeu HTTP {resposta.status}."
                dados = await resposta.json()
    except asyncio.TimeoutError:
        return None, "O GitHub demorou demais para responder."
    except Exception as erro:
        return None, f"Falha ao consultar o GitHub: {erro}"

    commit = dados.get("commit", {})
    return {
        "sha": dados.get("sha", ""),
        "mensagem": (commit.get("message") or "").strip().splitlines()[0] if commit.get("message") else "",
        "autor": (commit.get("author") or {}).get("name", "?"),
        "data": (commit.get("author") or {}).get("date", ""),
    }, None

async def listar_arquivos_repo(sha):
    """Arquivos de codigo do repositorio nesse commit."""
    url = f"https://api.github.com/repos/{REPO_GITHUB}/git/trees/{sha}?recursive=1"
    cabecalhos = {"Accept": "application/vnd.github+json", "User-Agent": "OrganicRP-Bot"}
    try:
        tempo = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=tempo) as sessao:
            async with sessao.get(url, headers=cabecalhos) as resposta:
                if resposta.status != 200:
                    return None, f"Não consegui listar os arquivos (HTTP {resposta.status})."
                dados = await resposta.json()
    except Exception as erro:
        return None, f"Falha ao listar arquivos: {erro}"

    arquivos = [
        item["path"] for item in dados.get("tree", [])
        if item.get("type") == "blob" and arquivo_e_atualizavel(item.get("path", ""))
    ]
    return arquivos, None

async def baixar_arquivo_repo(caminho_repo, sha):
    url = f"https://raw.githubusercontent.com/{REPO_GITHUB}/{sha}/{caminho_repo}"
    try:
        tempo = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=tempo) as sessao:
            async with sessao.get(url, headers={"User-Agent": "OrganicRP-Bot"}) as resposta:
                if resposta.status != 200:
                    return None, f"HTTP {resposta.status} ao baixar {caminho_repo}"
                return await resposta.read(), None
    except Exception as erro:
        return None, f"Falha ao baixar {caminho_repo}: {erro}"

def validar_codigo_python(conteudo, nome):
    """Trava de seguranca: codigo quebrado NAO pode ser gravado. Se o bot
    reiniciar com erro de sintaxe, ele morre e ninguem consegue mais subir
    nada remotamente."""
    if not conteudo or not conteudo.strip():
        return f"`{nome}` veio vazio do GitHub."
    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return f"`{nome}` não é UTF-8 válido."
    try:
        compile(texto, nome, "exec")
    except SyntaxError as erro:
        return f"`{nome}` tem erro de sintaxe (linha {erro.lineno}): {erro.msg}"
    return None

def preparar_pasta_backup():
    with suppress(Exception):
        if os.path.isdir(PASTA_BACKUP_UPDATE):
            shutil.rmtree(PASTA_BACKUP_UPDATE)
    os.makedirs(PASTA_BACKUP_UPDATE, exist_ok=True)

def salvar_backup_arquivo(caminho_local):
    if not os.path.exists(caminho_local):
        return
    destino = os.path.join(PASTA_BACKUP_UPDATE, os.path.relpath(caminho_local, BASE_DIR))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    shutil.copy2(caminho_local, destino)

def restaurar_backup():
    """Desfaz a atualizacao se algo falhar no meio."""
    if not os.path.isdir(PASTA_BACKUP_UPDATE):
        return 0
    restaurados = 0
    for raiz, _, arquivos in os.walk(PASTA_BACKUP_UPDATE):
        for arquivo in arquivos:
            origem = os.path.join(raiz, arquivo)
            destino = os.path.join(BASE_DIR, os.path.relpath(origem, PASTA_BACKUP_UPDATE))
            with suppress(Exception):
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                shutil.copy2(origem, destino)
                restaurados += 1
    return restaurados

def instalar_dependencias():
    try:
        resultado = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", os.path.join(BASE_DIR, "requirements.txt")],
            capture_output=True, text=True, timeout=600,
        )
        if resultado.returncode != 0:
            return (resultado.stderr or resultado.stdout or "").strip()[-500:]
        return None
    except Exception as erro:
        return str(erro)

def reiniciar_processo_bot():
    """Troca a imagem do processo pelo codigo novo. Funciona tanto rodando
    solto quanto sob systemd/pterodactyl."""
    print("[UPDATE] Reiniciando o processo para carregar o codigo novo...")
    sys.stdout.flush()
    os.execv(sys.executable, [sys.executable, os.path.abspath(sys.argv[0])] + sys.argv[1:])

def carregar_templates():
    return carregar_json_seguro(ARQUIVO_TEMPLATES, {})

def salvar_templates(dados):
    salvar_json_seguro(ARQUIVO_TEMPLATES, dados, ensure_ascii=False)

def remover_acentos(txt):
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

CARGOS_PERMITIDOS_NORM = {remover_acentos(nome).strip().lower() for nome in CARGOS_PERMITIDOS}

def usuario_e_staff(usuario):
    """Unica fonte de verdade sobre quem pode usar os recursos caros do bot
    (IA do Groq, transcricao do Gemini, RCON). Jogador comum sempre False.
    Retorna False fora de servidor (DM), onde nao existem cargos."""
    permissoes = getattr(usuario, "guild_permissions", None)
    if permissoes is not None and permissoes.administrator:
        return True

    for cargo in getattr(usuario, "roles", []) or []:
        if remover_acentos(cargo.name).strip().lower() in CARGOS_PERMITIDOS_NORM:
            return True

    return False

def participantes_elegiveis_sorteio(guild, participantes):
    """Remove bots e a staff dos participantes de um sorteio."""
    elegiveis = []
    for participante in participantes:
        if getattr(participante, "bot", False):
            continue
        # A lista da reacao pode devolver User em vez de Member. Recuperar o
        # membro do cache permite verificar corretamente cargos e permissoes.
        membro = guild.get_member(participante.id) or participante
        if usuario_e_staff(membro):
            continue
        elegiveis.append(participante)
    return elegiveis

def normalizar_chave_personagem(txt):
    txt = remover_acentos(txt or "").lower()
    return re.sub(r'\s+', ' ', txt).strip()

def compactar_chave_personagem(txt):
    return re.sub(r'[^a-z0-9]', '', normalizar_chave_personagem(txt))

def tokens_nome_personagem(txt):
    texto = normalizar_chave_personagem(txt)
    return [token for token in re.findall(r'[a-z0-9]+', texto) if len(token) >= 4]

def base_nome_sem_numeros(txt):
    compacto = compactar_chave_personagem(txt)
    return re.sub(r'\d+$', '', compacto)

def nomes_correspondentes_historico(nome_antigo, nome_novo):
    antigo_base = base_nome_sem_numeros(nome_antigo)
    novo_base = base_nome_sem_numeros(nome_novo)
    if not antigo_base or not novo_base:
        return False

    if antigo_base == novo_base:
        return True

    if len(antigo_base) >= 5 and (novo_base.startswith(antigo_base) or antigo_base.startswith(novo_base)):
        return True

    tokens_antigos = set(tokens_nome_personagem(nome_antigo))
    tokens_novos = set(tokens_nome_personagem(nome_novo))
    if tokens_antigos and tokens_antigos.intersection(tokens_novos):
        return True

    return False

def nomes_historicos_usuario(user_id_str, db_personagens=None):
    historico = carregar_historico_personagens()
    nomes = []

    for nome in historico.get(user_id_str, []):
        if isinstance(nome, str) and nome.strip():
            nomes.append(nome.strip())

    if db_personagens:
        personagem_atual = db_personagens.get(user_id_str)
        if personagem_atual:
            nomes.append(personagem_atual)

    nomes_unicos = []
    vistos = set()
    for nome in nomes:
        chave = compactar_chave_personagem(nome)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        nomes_unicos.append(nome)
    return nomes_unicos

def registrar_personagem_no_historico(user_id_str, nome_personagem):
    if not nome_personagem:
        return

    historico = carregar_historico_personagens()
    nomes = historico.get(user_id_str, [])
    if not isinstance(nomes, list):
        nomes = []

    chave_nova = compactar_chave_personagem(nome_personagem)
    if chave_nova and not any(compactar_chave_personagem(nome) == chave_nova for nome in nomes if isinstance(nome, str)):
        nomes.append(nome_personagem)

    historico[user_id_str] = nomes
    salvar_historico_personagens(historico)

def encontrar_nome_bloqueado_por_historico(user_id_str, nome_novo, db_personagens):
    for nome_antigo in nomes_historicos_usuario(user_id_str, db_personagens):
        if nomes_correspondentes_historico(nome_antigo, nome_novo):
            return nome_antigo
    return None

def sincronizar_historico_com_personagens_atuais():
    db_personagens = carregar_personagens()
    if not db_personagens:
        return

    historico = carregar_historico_personagens()
    alterou = False

    for user_id_str, nome_personagem in db_personagens.items():
        if not nome_personagem:
            continue

        nomes = historico.get(user_id_str, [])
        if not isinstance(nomes, list):
            nomes = []

        chave_atual = compactar_chave_personagem(nome_personagem)
        if chave_atual and not any(compactar_chave_personagem(nome) == chave_atual for nome in nomes if isinstance(nome, str)):
            nomes.append(nome_personagem)
            historico[user_id_str] = nomes
            alterou = True

    if alterou:
        salvar_historico_personagens(historico)

def salvar_ultimo_registro_personagem(message, nome_personagem, senha_personagem, historia_personagem="", profissao_personagem=""):
    if not message.guild or not nome_personagem or not senha_personagem:
        return

    user_id_str = str(message.author.id)
    registros = carregar_registros_personagens()
    registros[user_id_str] = {
        "discord_id": user_id_str,
        "discord_nome": str(message.author),
        "display_name": message.author.display_name,
        "personagem": nome_personagem,
        "senha": senha_personagem,
        "profissao": (profissao_personagem or "").strip(),
        "historia": (historia_personagem or "").strip(),
        "registrado_em": datetime.now().isoformat(),
        "guild_id": message.guild.id,
        "canal_id": message.channel.id,
    }
    salvar_registros_personagens(registros)

def sincronizar_registros_personagens_atuais():
    db_personagens = carregar_personagens()
    if not db_personagens:
        return

    registros = carregar_registros_personagens()
    alterou = False

    for user_id_str, nome_personagem in db_personagens.items():
        if not nome_personagem:
            continue

        registro_atual = registros.get(user_id_str, {})
        if registro_atual.get("personagem") == nome_personagem:
            continue

        registros[user_id_str] = {
            "discord_id": user_id_str,
            "discord_nome": registro_atual.get("discord_nome", ""),
            "display_name": registro_atual.get("display_name", ""),
            "personagem": nome_personagem,
            "senha": registro_atual.get("senha", ""),
            "profissao": registro_atual.get("profissao", ""),
            "historia": registro_atual.get("historia", ""),
            "registrado_em": registro_atual.get("registrado_em") or datetime.now().isoformat(),
            "guild_id": registro_atual.get("guild_id"),
            "canal_id": registro_atual.get("canal_id"),
        }
        alterou = True

    if alterou:
        salvar_registros_personagens(registros)

def formatar_data_registro(data_iso):
    try:
        return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return data_iso or "Não informado"

def formatar_texto_registro_embed(texto, padrao="Não disponível (registro antigo ou não informado)", limite=1000):
    texto = (texto or "").strip()
    if not texto:
        return padrao
    if len(texto) <= limite:
        return texto
    return texto[:limite - 3].rstrip() + "..."

def encontrar_membro_por_busca(guild, busca):
    if not guild or not busca:
        return None

    busca = busca.strip()
    id_alvo = "".join(filter(str.isdigit, busca))
    if id_alvo:
        membro = guild.get_member(int(id_alvo))
        if membro:
            return membro

    busca_norm = normalizar_chave_personagem(busca)
    for membro in guild.members:
        candidatos = [
            membro.name,
            membro.display_name,
            str(membro),
        ]
        if any(normalizar_chave_personagem(candidato) == busca_norm for candidato in candidatos if candidato):
            return membro

    for membro in guild.members:
        candidatos = [
            membro.name,
            membro.display_name,
            str(membro),
        ]
        if any(busca_norm in normalizar_chave_personagem(candidato) for candidato in candidatos if candidato):
            return membro

    return None

def montar_embed_registro_personagem(guild, membro, registro):
    embed = discord.Embed(title="📚 Registro de Personagem", color=discord.Color.blurple())
    embed.add_field(name="Jogador", value=f"{membro.mention}\n`{membro.id}`", inline=False)
    embed.add_field(name="Personagem Registrado", value=f"```{registro.get('personagem', 'Não informado')}```", inline=False)
    senha_registro = registro.get("senha") or "Não disponível (registro antigo)"
    embed.add_field(name="Senha Registrada", value=f"```{senha_registro}```", inline=False)
    profissao_registro = formatar_texto_registro_embed(
        registro.get("profissao"),
        padrao="Não informada (registro antigo ou não preenchida)",
        limite=256,
    )
    embed.add_field(name="Profissão Registrada", value=profissao_registro, inline=False)
    embed.add_field(name="História Registrada", value=formatar_texto_registro_embed(registro.get("historia")), inline=False)
    embed.add_field(name="Último Registro", value=f"`{formatar_data_registro(registro.get('registrado_em'))}`", inline=False)

    canal_id = registro.get("canal_id")
    if canal_id:
        canal = guild.get_channel(int(canal_id))
        if canal:
            embed.add_field(name="Canal", value=canal.mention, inline=False)

    return embed

def localizar_arquivos_mod(caminho_configurado, nomes_aceitos):
    """Acha um arquivo de dados do FriendHost testando os nomes conhecidos
    (novos em .csv.txt e os legados em .csv) e varrendo a pasta do mod.
    Devolve os existentes, do mais recente para o mais antigo."""
    candidatos = [caminho_configurado]
    for base in (os.path.join(CSV_BASE_PATH, "Servidor"), CSV_BASE_PATH):
        for nome in nomes_aceitos:
            candidatos.append(os.path.join(base, nome))

    nomes_baixos = {nome.lower() for nome in nomes_aceitos}
    with suppress(Exception):
        for raiz, _, arquivos in os.walk(CSV_BASE_PATH):
            for arquivo in arquivos:
                if arquivo.lower() in nomes_baixos:
                    candidatos.append(os.path.join(raiz, arquivo))

    vistos = set()
    existentes = []
    for caminho in candidatos:
        if not caminho:
            continue
        caminho = os.path.abspath(caminho)
        if caminho in vistos or not os.path.exists(caminho):
            continue
        vistos.add(caminho)
        existentes.append(caminho)

    with suppress(Exception):
        existentes.sort(key=os.path.getmtime, reverse=True)
    return existentes

def caminhos_players_online_friendhost():
    return localizar_arquivos_mod(CAMINHO_PLAYERS_ONLINE, NOMES_ARQUIVO_ONLINE)

def caminho_players_online_ativo():
    """Devolve a lista online mais recente exportada pelos mods.

    O ZomboidOSOnlinePlayersCSV so regrava online_players.txt quando alguem
    entra ou sai. Portanto, a data de modificacao nao mede se a lista e valida;
    a lista em si e o estado atual exportado pelo mod.
    """
    caminhos = caminhos_players_online_friendhost()
    if not caminhos:
        return None

    # Este TXT e atualizado pelo mod dedicado no login/logout e e a fonte
    # correta para a regra de 30 segundos. O CSV do FriendHost fica como
    # fallback, pois a configuracao padrao dele pode salvar so a cada 10 min.
    for caminho in caminhos:
        if os.path.basename(caminho).lower() == "online_players.txt":
            return caminho
    return caminhos[0]

def limpar_campo_csv(valor):
    return str(valor or "").replace('"', '').strip()

def construir_indices_personagens_atuais():
    db_personagens = carregar_personagens()
    indice_norm = {}
    indice_compacto = {}

    for user_id_str, nome_personagem in db_personagens.items():
        if not isinstance(nome_personagem, str) or not nome_personagem.strip():
            continue

        chave_norm = normalizar_chave_personagem(nome_personagem)
        chave_compacta = compactar_chave_personagem(nome_personagem)

        if chave_norm and chave_norm not in indice_norm:
            indice_norm[chave_norm] = (user_id_str, nome_personagem)
        if chave_compacta and chave_compacta not in indice_compacto:
            indice_compacto[chave_compacta] = (user_id_str, nome_personagem)

    return db_personagens, indice_norm, indice_compacto

def conectar_sqlite_somente_leitura(caminho):
    return sqlite3.connect(f"file:{caminho}?mode=ro", uri=True, timeout=1)

def carregar_roles_whitelist_jogo():
    roles_norm = {}
    roles_compacto = {}

    if not os.path.exists(WHITELIST_DB_PATH):
        return roles_norm, roles_compacto

    try:
        with conectar_sqlite_somente_leitura(WHITELIST_DB_PATH) as conn:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT w.username, w.displayName, w.role, r.name
                FROM whitelist w
                LEFT JOIN role r ON r.id = w.role
                WHERE w.username IS NOT NULL
                """
            ).fetchall()
    except Exception as erro:
        print(f"[CALL IN-GAME] Falha ao ler whitelist do jogo: {erro}")
        return roles_norm, roles_compacto

    for username, display_name, role_id, role_name in rows:
        info = {
            "username": (username or "").strip(),
            "display_name": (display_name or "").strip(),
            "role_id": int(role_id) if role_id is not None else None,
            "role_name": normalizar_chave_personagem(role_name or ""),
        }

        for candidato in (username, display_name):
            chave_norm = normalizar_chave_personagem(candidato)
            chave_compacta = compactar_chave_personagem(candidato)
            if chave_norm and chave_norm not in roles_norm:
                roles_norm[chave_norm] = info
            if chave_compacta and chave_compacta not in roles_compacto:
                roles_compacto[chave_compacta] = info

    return roles_norm, roles_compacto

def linha_parece_cabecalho_online_players(campos_limpos):
    if not campos_limpos:
        return False

    cabecalhos = {"username", "user", "player", "players", "name", "nickname"}
    texto = " ".join(normalizar_chave_personagem(campo) for campo in campos_limpos).strip()
    return texto in cabecalhos

def carregar_vinculos_networkplayers_jogo(indice_norm, indice_compacto):
    vinculos_norm = {}
    vinculos_compacto = {}

    if not os.path.exists(PLAYERS_DB_PATH):
        return vinculos_norm, vinculos_compacto

    try:
        with conectar_sqlite_somente_leitura(PLAYERS_DB_PATH) as conn:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT id, username, name
                FROM networkPlayers
                WHERE username IS NOT NULL OR name IS NOT NULL
                ORDER BY id DESC
                """
            ).fetchall()
    except Exception as erro:
        print(f"[CALL IN-GAME] Falha ao ler networkPlayers: {erro}")
        return vinculos_norm, vinculos_compacto

    for _, username, nome_personagem in rows:
        username_limpo = limpar_campo_csv(username)
        nome_limpo = limpar_campo_csv(nome_personagem)

        user_id_str = None
        personagem_atual = None

        for candidato in (nome_limpo, username_limpo):
            chave_norm = normalizar_chave_personagem(candidato)
            chave_compacta = compactar_chave_personagem(candidato)
            if chave_norm in indice_norm:
                user_id_str, personagem_atual = indice_norm[chave_norm]
                break
            if chave_compacta in indice_compacto:
                user_id_str, personagem_atual = indice_compacto[chave_compacta]
                break

        if not user_id_str or not personagem_atual:
            continue

        info = {
            "discord_id": user_id_str,
            "personagem": personagem_atual,
            "username_jogo": username_limpo or nome_limpo,
            "nome_network": nome_limpo,
        }

        for candidato in (username_limpo, nome_limpo):
            chave_norm = normalizar_chave_personagem(candidato)
            chave_compacta = compactar_chave_personagem(candidato)
            if chave_norm and chave_norm not in vinculos_norm:
                vinculos_norm[chave_norm] = info
            if chave_compacta and chave_compacta not in vinculos_compacto:
                vinculos_compacto[chave_compacta] = info

    return vinculos_norm, vinculos_compacto

def identificar_role_jogo(campos_limpos, nome_personagem, username_jogo, roles_norm, roles_compacto):
    candidatos = list(campos_limpos)
    if nome_personagem:
        candidatos.append(nome_personagem)
    if username_jogo:
        candidatos.append(username_jogo)

    for candidato in candidatos:
        chave_norm = normalizar_chave_personagem(candidato)
        chave_compacta = compactar_chave_personagem(candidato)
        info = roles_norm.get(chave_norm) or roles_compacto.get(chave_compacta)
        if info:
            return info

    return None

def encontrar_membro_discord_por_nome_personagem(nome_personagem):
    """Procura um membro pelo nome/apelido exibido no Discord.

    E um fallback para personagens antigos ou criados fora do fluxo do bot,
    que ainda nao aparecem em personagens.json. So aceita correspondencia
    exata e unica para nunca associar o jogador errado.
    """
    chave_norm = normalizar_chave_personagem(nome_personagem)
    chave_compacta = compactar_chave_personagem(nome_personagem)
    if not chave_norm:
        return None

    encontrados = {}
    for guild in bot.guilds:
        for membro in guild.members:
            candidatos = [
                membro.display_name,
                membro.name,
                getattr(membro, "global_name", None),
            ]
            for candidato in candidatos:
                if not candidato:
                    continue
                if (
                    normalizar_chave_personagem(candidato) == chave_norm
                    or compactar_chave_personagem(candidato) == chave_compacta
                ):
                    encontrados[membro.id] = membro
                    break

    return next(iter(encontrados.values())) if len(encontrados) == 1 else None

def identificar_jogador_online_por_linha(campos, db_personagens, indice_norm, indice_compacto, vinculos_norm, vinculos_compacto, roles_norm, roles_compacto):
    candidatos = {}
    campos_limpos = [limpar_campo_csv(campo) for campo in campos if limpar_campo_csv(campo)]

    if linha_parece_cabecalho_online_players(campos_limpos):
        return None

    for campo in campos_limpos:
        chave_norm = normalizar_chave_personagem(campo)
        chave_compacta = compactar_chave_personagem(campo)

        vinculo = vinculos_norm.get(chave_norm) or vinculos_compacto.get(chave_compacta)
        if vinculo:
            candidatos[vinculo["discord_id"]] = {
                "discord_id": vinculo["discord_id"],
                "personagem": vinculo["personagem"],
                "username_jogo": vinculo.get("username_jogo"),
            }
            continue

        if chave_norm in indice_norm:
            user_id_str, nome_personagem = indice_norm[chave_norm]
            candidatos[user_id_str] = {
                "discord_id": user_id_str,
                "personagem": nome_personagem,
                "username_jogo": campo,
            }
            continue

        if chave_compacta in indice_compacto:
            user_id_str, nome_personagem = indice_compacto[chave_compacta]
            candidatos[user_id_str] = {
                "discord_id": user_id_str,
                "personagem": nome_personagem,
                "username_jogo": campo,
            }
            continue

    if len(candidatos) == 1:
        jogador = next(iter(candidatos.values()))
        role_info = identificar_role_jogo(
            campos_limpos,
            jogador["personagem"],
            jogador.get("username_jogo"),
            roles_norm,
            roles_compacto,
        )
        return {
            "discord_id": jogador["discord_id"],
            "personagem": jogador["personagem"],
            "username_jogo": jogador.get("username_jogo") or (role_info or {}).get("username"),
            "role_id": (role_info or {}).get("role_id"),
            "role_name": (role_info or {}).get("role_name"),
        }

    # A lista online pode conter personagens antigos que nao foram criados
    # pelo bot e por isso nao existem no banco local. No servidor, o apelido
    # do Discord normalmente e o nome do personagem; use-o apenas se for uma
    # correspondencia exata e sem ambiguidade.
    if not candidatos and campos_limpos:
        membro = encontrar_membro_discord_por_nome_personagem(campos_limpos[0])
        if membro:
            nome_personagem = campos_limpos[0]
            role_info = identificar_role_jogo(
                campos_limpos, nome_personagem, nome_personagem,
                roles_norm, roles_compacto,
            )
            return {
                "discord_id": str(membro.id),
                "personagem": nome_personagem,
                "username_jogo": (role_info or {}).get("username") or nome_personagem,
                "role_id": (role_info or {}).get("role_id"),
                "role_name": (role_info or {}).get("role_name"),
            }

    if len(campos_limpos) <= 1:
        return None

    linha_norm = " | ".join(normalizar_chave_personagem(campo) for campo in campos_limpos)
    linha_compacta = compactar_chave_personagem(" ".join(campos_limpos))

    if not candidatos:
        for user_id_str, nome_personagem in db_personagens.items():
            nome_norm = normalizar_chave_personagem(nome_personagem)
            nome_compacto = compactar_chave_personagem(nome_personagem)

            if nome_norm and len(nome_norm) >= 5 and nome_norm in linha_norm:
                candidatos[user_id_str] = nome_personagem
                continue

            if nome_compacto and len(nome_compacto) >= 5 and nome_compacto in linha_compacta:
                candidatos[user_id_str] = nome_personagem

    if len(candidatos) == 1:
        user_id_str, nome_personagem = next(iter(candidatos.items()))
        role_info = identificar_role_jogo(campos_limpos, nome_personagem, "", roles_norm, roles_compacto)
        return {
            "discord_id": user_id_str,
            "personagem": nome_personagem,
            "username_jogo": (role_info or {}).get("username") or (campos_limpos[0] if campos_limpos else ""),
            "role_id": (role_info or {}).get("role_id"),
            "role_name": (role_info or {}).get("role_name"),
        }

    return None

def ler_jogadores_online_friendhost():
    caminho = caminho_players_online_ativo()
    if not caminho:
        return {}

    db_personagens, indice_norm, indice_compacto = construir_indices_personagens_atuais()
    roles_norm, roles_compacto = carregar_roles_whitelist_jogo()
    vinculos_norm, vinculos_compacto = carregar_vinculos_networkplayers_jogo(indice_norm, indice_compacto)
    if not db_personagens:
        return {}

    jogadores_online = {}

    try:
        with open(caminho, "r", encoding="utf-8", errors="replace", newline="") as f:
            # O formato novo tem um username por linha; csv.reader tambem
            # interpreta corretamente os CSVs legados separados por ';'.
            leitor = csv.reader(f, delimiter=";")
            for row in leitor:
                jogador = identificar_jogador_online_por_linha(
                    row,
                    db_personagens,
                    indice_norm,
                    indice_compacto,
                    vinculos_norm,
                    vinculos_compacto,
                    roles_norm,
                    roles_compacto,
                )
                if not jogador:
                    continue
                jogadores_online[jogador["discord_id"]] = {
                    "personagem": jogador["personagem"],
                    "username_jogo": jogador.get("username_jogo"),
                    "role_id": jogador.get("role_id"),
                    "role_name": jogador.get("role_name"),
                    "fonte": caminho,
                }
    except Exception as erro:
        print(f"[CALL IN-GAME] Falha ao ler jogadores online em {caminho}: {erro}")

    return jogadores_online

def conteudo_lista_jogadores_rcon(resposta):
    """Normaliza a saida do comando RCON ``players`` para uma lista simples.

    O console costuma prefixar cada jogador com numero, por exemplo
    ``1. Adrian Cross``. O parser de registros trabalha apenas com o nome.
    """
    linhas = []
    for linha in (resposta or "").splitlines():
        # O RCON pode listar como "1. Nome", "2) Nome" ou "-Nome".
        # Todos esses prefixos precisam sair antes de comparar com o registro.
        linha = re.sub(r"^\s*(?:\d+\s*[.)-]\s*|[-•]\s*)", "", linha).strip()
        if not linha:
            continue
        chave = normalizar_chave_personagem(linha)
        if chave.startswith(("players connected", "players online", "online players", "there are no players")):
            continue
        linhas.append(linha)
    return "\n".join(linhas)

def identificar_jogadores_online_por_conteudo(conteudo, fonte):
    """Vincula nomes vindos do RCON aos IDs do Discord registrados no bot."""
    db_personagens, indice_norm, indice_compacto = construir_indices_personagens_atuais()
    roles_norm, roles_compacto = carregar_roles_whitelist_jogo()
    vinculos_norm, vinculos_compacto = carregar_vinculos_networkplayers_jogo(indice_norm, indice_compacto)
    if not db_personagens:
        return {}

    jogadores_online = {}
    for row in csv.reader((conteudo or "").splitlines(), delimiter=";"):
        jogador = identificar_jogador_online_por_linha(
            row,
            db_personagens,
            indice_norm,
            indice_compacto,
            vinculos_norm,
            vinculos_compacto,
            roles_norm,
            roles_compacto,
        )
        if not jogador:
            continue
        jogadores_online[jogador["discord_id"]] = {
            "personagem": jogador["personagem"],
            "username_jogo": jogador.get("username_jogo"),
            "role_id": jogador.get("role_id"),
            "role_name": jogador.get("role_name"),
            "fonte": fonte,
        }
    return jogadores_online

async def ler_jogadores_online_monitoramento():
    """Le o TXT dos mods; sem volume compartilhado, usa RCON como fallback."""
    caminho = await asyncio.to_thread(caminho_players_online_ativo)
    if caminho:
        return await asyncio.to_thread(ler_jogadores_online_friendhost)

    resultado = await enviar_comando_rcon_detalhado("players")
    if not resultado.ok:
        print(f"[CALL IN-GAME] Nao achei online_players.txt e o RCON players falhou: {resultado.error}")
        return {}

    conteudo = conteudo_lista_jogadores_rcon(resultado.output)
    return identificar_jogadores_online_por_conteudo(conteudo, "RCON players")

def nomes_calls_permitidas():
    nomes = [NOME_CALL_INGAME]
    nomes.extend(CANAIS_CALL_PERMITIDAS_RAW.split(","))
    return {
        normalizar_chave_personagem(nome)
        for nome in nomes
        if normalizar_chave_personagem(nome)
    }

def canal_e_call_ingame(canal):
    """Retorna se o canal e uma das calls oficiais que contam para a regra.

    O Discord inclui emojis e separadores no nome visual dos canais. Por isso
    o texto permitido pode estar dentro do nome, mas com borda de palavra para
    que ``Atendimento 1`` nao aceite por engano ``Atendimento 10``.
    """
    nome = normalizar_chave_personagem(getattr(canal, "name", ""))
    for alvo in nomes_calls_permitidas():
        if re.search(r"(?<![a-z0-9])" + re.escape(alvo) + r"(?![a-z0-9])", nome):
            return True
    return False

def ids_na_call_ingame():
    """IDs nas calls oficiais: in-game, espera, atendimentos e trabalhando."""
    ids = set()
    for guild in bot.guilds:
        for canal in list(guild.voice_channels) + list(guild.stage_channels):
            if not canal_e_call_ingame(canal):
                continue
            ids.update(membro.id for membro in canal.members if not membro.bot)
    return ids

def ids_em_qualquer_call_servidor():
    ids = set()

    for guild in bot.guilds:
        for canal in list(guild.voice_channels) + list(guild.stage_channels):
            ids.update(membro.id for membro in canal.members if not membro.bot)

    return ids

def jogador_isento_call_ingame(user_id_str, dados):
    """Quem NAO pode ser expulso: admin/moderador do jogo ou staff do Discord.

    Antes a regra era 'so expulsa se role_id == 2'. Isso significava que qualquer
    jogador sem role identificada (whitelist do jogo ilegivel, caminho errado
    depois da troca de host) ficava imune - e ninguem era expulso."""
    role_name = normalizar_chave_personagem(dados.get("role_name") or "")
    isentos = [
        normalizar_chave_personagem(c)
        for c in CARGOS_JOGO_ISENTOS_CALL_RAW.split(",") if c.strip()
    ]
    if role_name and any(cargo and cargo in role_name for cargo in isentos):
        return True, f"cargo no jogo ({role_name})"

    for guild in bot.guilds:
        membro = guild.get_member(int(user_id_str)) if user_id_str else None
        if membro and usuario_e_staff(membro):
            return True, "staff do Discord"

    return False, ""

def classificar_resposta_rcon_kick(resposta):
    texto = (resposta or "").lower().strip()
    if not texto:
        return "ok"

    if any(padrao in texto for padrao in ("unknown command", "no such command", "usage:")):
        return "comando_invalido"

    if any(padrao in texto for padrao in ("doesn't exist", "does not exist", "not found", "no such user")):
        return "usuario_nao_encontrado"

    if any(padrao in texto for padrao in ("error", "failed", "exception")):
        return "erro"

    return "ok"

async def avisar_jogador_expulso_call(user_id_str, nome_personagem):
    """Avisa no Discord, alem da mensagem que o jogo ja mostra na tela do kick."""
    membro = None
    for guild in bot.guilds:
        with suppress(Exception):
            membro = guild.get_member(int(user_id_str))
        if membro:
            break
    if not membro:
        return

    texto = (
        f"🔇 **Você foi desconectado do servidor.**\n\n"
        f"Personagem: **{nome_personagem}**\n"
        f"Motivo: você estava jogando **sem estar na call `{NOME_CALL_INGAME}`** do Discord.\n\n"
        f"Entrar em outra call (OFF game, pós-sessão, etc.) **não conta** — precisa ser a call in-game.\n"
        f"Entre nela e pode conectar de novo no servidor."
    )

    with suppress(Exception):
        await membro.send(texto)
        return

    # DM bloqueada: avisa no canal de status, se existir.
    if CANAL_STATUS_ID:
        with suppress(Exception):
            canal = bot.get_channel(int(CANAL_STATUS_ID))
            if canal:
                await canal.send(f"{membro.mention} {texto}", delete_after=120)

async def expulsar_jogador_sem_call_ingame(username_jogo, nome_personagem=""):
    """Expulsa pelo username de login do PZ, nao pelo nome do personagem.

    O mod ZomboidOSOnlinePlayersCSV atualizado exporta ``player:getUsername()``
    e o comando RCON ``kickuser`` recebe exatamente esse identificador.
    ``nome_personagem`` permanece apenas como fallback para os CSVs legados.
    """
    alvo = (username_jogo or nome_personagem or "").strip()
    if not alvo:
        return False, "arquivo online sem username e sem nome de personagem"

    comandos = [
        f'kickuser "{alvo}" -r "{MENSAGEM_KICK_CALL_INGAME}"',
        f'kick "{alvo}" -r "{MENSAGEM_KICK_CALL_INGAME}"',
    ]

    ultimo_erro = ""

    for comando in comandos:
        resultado = await enviar_comando_rcon_detalhado(comando)
        if not resultado.ok:
            ultimo_erro = resultado.error or "falha desconhecida no RCON"
            break

        classificacao = classificar_resposta_rcon_kick(resultado.output)
        if classificacao == "ok":
            return True, resultado.output or "kick enviado com sucesso"

        if classificacao == "usuario_nao_encontrado":
            # Pode ter desconectado entre a leitura e o kick, ou o primeiro
            # comando pode nao aceitar esse formato de nome. Tenta o proximo
            # comando e nunca avisa o Discord como se o kick tivesse ocorrido.
            ultimo_erro = resultado.output or "jogador nao encontrado no momento do kick"
            continue

        if classificacao == "comando_invalido":
            ultimo_erro = resultado.output or "comando de kick inválido"
            continue

        ultimo_erro = resultado.output or "o servidor rejeitou o comando de kick"

    return False, ultimo_erro or "não consegui expulsar o jogador"

def caminhos_mortes_friendhost():
    return localizar_arquivos_mod(CAMINHO_MORTES, NOMES_ARQUIVO_MORTES)

def caminhos_logs_morte_friendhost(max_arquivos=40):
    bases = [LOGS_PATH, TXT_BASE_PATH]
    padroes = ("perklog", "friendhost", "cmd", "user", "debuglog-server")
    encontrados = []
    vistos = set()

    for base in bases:
        if not base or not os.path.isdir(base):
            continue
        with suppress(Exception):
            for raiz, _, arquivos in os.walk(base):
                for arquivo in arquivos:
                    nome = arquivo.lower()
                    if not nome.endswith((".txt", ".log")):
                        continue
                    if not any(padrao in nome for padrao in padroes):
                        continue
                    caminho = os.path.join(raiz, arquivo)
                    caminho_abs = os.path.abspath(caminho)
                    if caminho_abs in vistos:
                        continue
                    vistos.add(caminho_abs)
                    encontrados.append(caminho_abs)

    encontrados.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return encontrados[:max_arquivos]

def detectar_rotacao_arquivo(caminho, posicao_atual):
    """True quando o arquivo encolheu, sinal de que o host rotacionou ou zerou o
    log. Sem isso o tail fica lendo um arquivo que nunca mais cresce."""
    try:
        return os.stat(caminho).st_size < posicao_atual
    except Exception:
        return False

def ler_final_arquivo(caminho, limite_bytes=2 * 1024 * 1024):
    with open(caminho, "rb") as f:
        f.seek(0, os.SEEK_END)
        tamanho = f.tell()
        f.seek(max(0, tamanho - limite_bytes))
        return f.read().decode("utf-8", errors="replace")

def linha_morte_tem_personagem(texto_linha, nome_personagem):
    linha_norm = normalizar_chave_personagem(texto_linha)
    nome_norm = normalizar_chave_personagem(nome_personagem)
    nome_compacto = compactar_chave_personagem(nome_personagem)

    if not nome_norm:
        return False

    if nome_norm in linha_norm:
        return True

    if nome_compacto and nome_compacto in compactar_chave_personagem(texto_linha):
        return True

    return False

MARCADORES_MORTE = ("died", "death", "morreu", "morte", "sendplayerdatadead", "is dead")

def linha_indica_morte(linha):
    baixa = remover_acentos(linha or "").lower()
    return any(marcador in baixa for marcador in MARCADORES_MORTE)

def campos_estruturados_morte(linha):
    """Se a linha vier em colunas (o mod usa ';'), devolve os campos.
    Vale tanto para o .csv antigo quanto para um .txt com o mesmo layout."""
    for separador in (";", "|", "\t"):
        if (linha or "").count(separador) >= 3:
            return [campo.strip().strip('"').strip() for campo in linha.split(separador)]
    return []

# Formato do LogExtender do FriendHost. A linha final fica assim:
#   [06-08-26 14:23:11.123] [Fulano] [PLAYER] 76561198... "Fulano" death perks={...}
# As acoes possiveis sao death / connected / levelup / tick, e o MESMO arquivo
# recebe [CHAT], [CMD] etc. Por isso a acao precisa ser lida com precisao: se o
# jogador escrever "morri" no chat, isso NAO pode virar uma morte.
RE_ACAO_PLAYER_LOGEXTENDER = re.compile(r'\[PLAYER\]\s+\S+\s+"([^"]*)"\s+([A-Za-z]+)')
FILEMASKS_LOGEXTENDER = {
    "CHAT", "USER", "CMD", "ITEM", "MAP", "PVP", "VEHICLE", "PLAYER",
    "ADMIN", "SAFEHOUSE", "CRAFT", "MAP_ALTERNATIVE", "BRUSHTOOL",
}
RE_FILEMASK = re.compile(r"\[([A-Z][A-Z_]{2,19})\]")

def nomes_na_linha_morte(linha):
    """Nomes de personagem citados numa linha de morte.

    IMPORTANTE: o CSV do mod ordena as colunas ALFABETICAMENTE pelo nome do
    campo (ADGetCSVHeader/ADGetCSVLine). Basta o mod adicionar um campo novo
    para as posicoes mudarem. Por isso nao existe indice fixo aqui: devolvemos
    todos os campos de texto como candidatos e a comparacao e feita por valor.
    """
    linha = linha or ""
    nomes = []

    # 1) Log do LogExtender: nome vem entre aspas, logo antes da acao.
    correspondencia = RE_ACAO_PLAYER_LOGEXTENDER.search(linha)
    if correspondencia:
        return _limpar_nomes_morte([correspondencia.group(1)])

    # 2) CSV do mod (deaths.csv.txt): qualquer campo de texto pode ser o nome.
    campos = campos_estruturados_morte(linha)
    if campos:
        nomes.extend(campos)

    # 3) Log em texto de outros formatos.
    nomes.extend(re.findall(r'"([^"]{2,40})"', linha))
    for padrao in (
        r"(?i)\b(?:user|player|jogador)\s+([A-Za-z0-9_][A-Za-z0-9_ ]{1,39}?)\s+(?:died|is dead|morreu)",
        r"(?i)\b([A-Za-z0-9_][A-Za-z0-9_ ]{1,39}?)\s+(?:died|morreu)\b",
    ):
        nomes.extend(re.findall(padrao, linha))

    return _limpar_nomes_morte(nomes)

def _limpar_nomes_morte(nomes):
    vistos = set()
    limpos = []
    for nome in nomes:
        nome = (nome or "").strip().strip('"').strip()
        chave = normalizar_chave_personagem(nome)
        # Descarta numero puro (id, timestamp, coordenada) e campo vazio.
        if not chave or not re.search(r"[A-Za-zÀ-ÿ]", nome):
            continue
        if chave in vistos:
            continue
        vistos.add(chave)
        limpos.append(nome)
    return limpos

def extrair_morte_da_linha(linha):
    """Porta de entrada unica da deteccao de morte.

    Devolve:
      None  -> a linha NAO e um registro de morte (ignorar)
      []    -> e morte, mas nao deu para extrair o nome
      [...] -> nomes envolvidos na morte

    A regra critica esta aqui: linha em texto livre so conta como morte se
    disser explicitamente (died/morreu/...). Sem isso, um simples
    'user "Fulano" connected' liberaria o jogador para recriar estando vivo.
    """
    linha = linha or ""
    if not linha.strip():
        return None

    # 1) Log do LogExtender: a acao decide. Só "death" conta.
    correspondencia = RE_ACAO_PLAYER_LOGEXTENDER.search(linha)
    if correspondencia:
        if correspondencia.group(2).lower() not in ("death", "died", "dead"):
            return None  # connected / levelup / tick
        return _limpar_nomes_morte([correspondencia.group(1)])

    # 2) Outras categorias do LogExtender ([CHAT], [CMD]...) nunca sao morte.
    #    Sem isso, alguem escrevendo "morri" no chat liberaria o registro.
    if any(mask in FILEMASKS_LOGEXTENDER for mask in RE_FILEMASK.findall(linha)):
        return None

    # 3) CSV do mod. O deaths.csv.txt so recebe linha quando isAlive=false,
    #    entao toda linha de dados ali ja e uma morte.
    if len(campos_estruturados_morte(linha)) >= 4:
        return nomes_na_linha_morte(linha)

    # 4) Texto livre: exige marcador explicito de morte.
    if not linha_indica_morte(linha):
        return None

    return nomes_na_linha_morte(linha)

def filtrar_nomes_registrados(nomes):
    """Mantem apenas os nomes que correspondem a um personagem registrado.

    O CSV do mod traz varias colunas (data, profissao, coordenada...). Sem esse
    filtro o monitor gravaria lixo como 'morto' no banco de status."""
    _, indice_norm, indice_compacto = construir_indices_personagens_atuais()
    encontrados = []
    for nome in nomes:
        if normalizar_chave_personagem(nome) in indice_norm or compactar_chave_personagem(nome) in indice_compacto:
            encontrados.append(nome)
    return encontrados

def nome_bate_com_morte(nome_personagem, nomes_linha, linha):
    nome_norm = normalizar_chave_personagem(nome_personagem)
    nome_compacto = compactar_chave_personagem(nome_personagem)
    if not nome_norm:
        return False

    for candidato in nomes_linha:
        candidato_norm = normalizar_chave_personagem(candidato)
        if candidato_norm == nome_norm:
            return True
        if nome_compacto and compactar_chave_personagem(candidato) == nome_compacto:
            return True

    # Formato desconhecido: cai na comparacao direta contra a linha inteira.
    if not nomes_linha:
        return linha_morte_tem_personagem(linha, nome_personagem)

    return False

def personagem_morreu_no_csv(nome_personagem):
    """Procura a morte no arquivo do mod, seja ele .csv ou .txt."""
    if not normalizar_chave_personagem(nome_personagem):
        return False

    for caminho in caminhos_mortes_friendhost():
        try:
            conteudo = ler_final_arquivo(caminho)
            for linha in conteudo.splitlines():
                nomes = extrair_morte_da_linha(linha)
                if nomes is None:
                    continue
                if nome_bate_com_morte(nome_personagem, nomes, linha):
                    return True
        except Exception as erro:
            print(f"[MORTES] Falha ao ler arquivo de mortes {caminho}: {erro}")

    return False

def personagem_morreu_nos_logs(nome_personagem):
    for caminho in caminhos_logs_morte_friendhost():
        try:
            conteudo = ler_final_arquivo(caminho)
            for linha in conteudo.splitlines():
                linha_baixa = remover_acentos(linha).lower()
                if not any(marcador in linha_baixa for marcador in ("died", "death", "morreu", "sendplayerdatadead")):
                    continue
                if linha_morte_tem_personagem(linha, nome_personagem):
                    return True
        except Exception as erro:
            print(f"[MORTES] Falha ao ler log de mortes {caminho}: {erro}")

    return False

def personagem_esta_morto(nome_personagem):
    return personagem_morreu_no_csv(nome_personagem) or personagem_morreu_nos_logs(nome_personagem)

def categoria_processa_ficha_pos_morte(categoria):
    if not categoria:
        return False

    nome_categoria = remover_acentos(categoria.name).lower()
    return "morte" in nome_categoria or "criacao de personagem" in nome_categoria

ROTULOS_NOME_FICHA = [
    "nome/sobrenome",
    "nome completo",
    "nome do personagem",
    "nome personagem",
    "personagem",
    "usuario",
    "usuário",
    "login",
    "nick",
    "nome",
]

ROTULOS_SENHA_FICHA = [
    "senha para entrar",
    "senha de entrada",
    "senha do servidor",
    "password",
    "pass",
    "senha",
]

ROTULOS_PROFISSAO_FICHA = [
    "profissao do personagem",
    "profissão do personagem",
    "profissao/ocupacao",
    "profissão/ocupação",
    "profissao",
    "profissão",
    "ocupacao",
    "ocupação",
    "profissional",
    "profession",
    "occupation",
    "emprego",
    "trabalho",
]

ROTULOS_HISTORIA_FICHA = [
    "historia do personagem",
    "história do personagem",
    "historia",
    "história",
    "bio",
    "biografia",
    "lore",
    "background",
    "backstory",
]

def regex_rotulos_ficha(rotulos):
    return "|".join(re.escape(rotulo) for rotulo in rotulos)

def normalizar_texto_ficha(texto):
    texto = texto or ""
    texto = re.sub(r'[*`_~\u200b]', '', texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    return texto

def limpar_valor_ficha(valor, multilinha=False):
    valor = re.sub(r'^[\s:=>\-–—•|]+', '', valor or "").strip()
    valor = re.sub(r'^(?:e|eh|é)\s+', '', valor, flags=re.IGNORECASE).strip()

    linhas_validas = []
    for linha in valor.splitlines():
        linha = re.sub(r'^[\s:=>\-–—•|]+', '', linha).strip()
        linha = re.sub(r'^(?:e|eh|é)\s+', '', linha, flags=re.IGNORECASE).strip()
        if linha and re.search(r'[A-Za-zÀ-ÿ0-9]', linha):
            linha = linha.strip(' "\'')
            if not multilinha:
                return linha
            linhas_validas.append(linha)

    if multilinha and linhas_validas:
        return "\n".join(linhas_validas).strip()

    return ""

def extrair_valor_ficha(texto, rotulos_alvo, rotulos_outros):
    texto = normalizar_texto_ficha(texto)
    padrao_alvo = regex_rotulos_ficha(rotulos_alvo)
    padrao_todos = regex_rotulos_ficha(rotulos_alvo + rotulos_outros)
    rotulo_re = re.compile(rf'(?i)(?<!\w)(?:{padrao_alvo})(?!\w)\s*(?:[:=]|\-+|–|—|=>)?')
    todos_re = re.compile(rf'(?i)(?<!\w)(?:{padrao_todos})(?!\w)\s*(?:[:=]|\-+|–|—|=>)?')

    for match in rotulo_re.finditer(texto):
        inicio = match.end()
        proximo = todos_re.search(texto, inicio)
        fim_rotulo = proximo.start() if proximo else len(texto)
        fim_linha = texto.find("\n", inicio)

        if fim_linha != -1 and fim_linha < fim_rotulo:
            trecho_linha = texto[inicio:fim_linha]
            if limpar_valor_ficha(trecho_linha):
                fim_rotulo = fim_linha

        valor = limpar_valor_ficha(texto[inicio:fim_rotulo])
        if valor:
            return valor

    return ""

def extrair_valor_ficha_multilinha(texto, rotulos_alvo, rotulos_outros):
    texto = normalizar_texto_ficha(texto)
    padrao_alvo = regex_rotulos_ficha(rotulos_alvo)
    padrao_todos = regex_rotulos_ficha(rotulos_alvo + rotulos_outros)
    rotulo_re = re.compile(
        rf'(?is)(?:^|\n)\s*(?:{padrao_alvo})(?!\w)\s*(?:[:=]|\-+|–|—|=>)?\s*(.+?)(?=(?:\n\s*(?:{padrao_todos})(?!\w)\s*(?:[:=]|\-+|–|—|=>)?)|\Z)'
    )

    for match in rotulo_re.finditer(texto):
        valor = limpar_valor_ficha(match.group(1), multilinha=True)
        if valor:
            return valor

    return ""

def extrair_dados_ficha(texto):
    return (
        extrair_valor_ficha(texto, ROTULOS_NOME_FICHA, ROTULOS_SENHA_FICHA + ROTULOS_PROFISSAO_FICHA),
        extrair_valor_ficha(texto, ROTULOS_SENHA_FICHA, ROTULOS_NOME_FICHA + ROTULOS_PROFISSAO_FICHA),
    )

def extrair_profissao_ficha(texto):
    return extrair_valor_ficha(
        texto,
        ROTULOS_PROFISSAO_FICHA,
        ROTULOS_NOME_FICHA + ROTULOS_SENHA_FICHA + ROTULOS_HISTORIA_FICHA,
    )

def extrair_historia_ficha(texto):
    return extrair_valor_ficha_multilinha(
        texto,
        ROTULOS_HISTORIA_FICHA,
        ROTULOS_NOME_FICHA + ROTULOS_SENHA_FICHA + ROTULOS_PROFISSAO_FICHA,
    )

def mensagem_parece_formulario_ficha(message):
    if message.author.bot:
        return False

    nome, senha = extrair_dados_ficha(message.content)
    return bool(nome or senha)

def mensagem_bot_indica_ficha_processada(message):
    if message.author != bot.user:
        return False

    texto = remover_acentos(message.content or "").lower()
    marcadores = [
        "ficha aprovada",
        "ficha recebida",
        "registro concluido",
        "registro cancelado",
        "registro nao concluido",
        "falha critica",
        "sistema anti-fraude",
        "sua ficha ja esta na fila",
        "servidor esta offline",
        "tirando sua ficha da fila",
    ]

    if any(p in texto for p in marcadores):
        return True

    for embed in message.embeds:
        titulo = remover_acentos(embed.title or "").lower()
        descricao = remover_acentos(embed.description or "").lower()
        if any(p in titulo or p in descricao for p in ("registro concluido", "ficha recebida")):
            return True

    return False

# --- FORMULARIO EM MODAL ---

class FichaSubmetida:
    """Adaptador que faz os dados vindos do Modal se comportarem como uma
    discord.Message. Assim o processar_registro_pos_morte continua com UM unico
    caminho de validacao (anti-fraude, morte, RCON) para ficha digitada e ficha
    do formulario."""

    def __init__(self, conteudo, autor, canal, guild, ancora_id):
        self.content = conteudo
        self.author = autor
        self.channel = canal
        self.guild = guild
        self.id = ancora_id
        self.embeds = []
        self.via_modal = True

def normalizar_campo_modal(valor, multilinha=False):
    """Tira markdown e quebras de linha indevidas do que o jogador digitou."""
    valor = re.sub(r'[*`_~​]', '', valor or "").strip()
    if not multilinha:
        valor = " ".join(valor.split())
    return valor

def montar_texto_ficha(nome, senha, profissao, historia):
    """Remonta a ficha no formato de texto que os extratores ja entendem.
    A historia fica por ultimo de proposito: se o jogador escrever algo como
    'Senha: x' dentro dela, os extratores ja terao pego os valores reais das
    primeiras linhas."""
    linhas = [
        f"Nome/Sobrenome: {nome}",
        f"Senha para entrar: {senha}",
    ]
    if profissao:
        linhas.append(f"Profissão: {profissao}")
    if historia:
        linhas.append(f"História do personagem: {historia}")
    return "\n".join(linhas)

def canal_tem_ficha_em_analise(canal_id):
    return any(a.get("canal_id") == canal_id for a in carregar_fichas_em_analise())

def ficha_ativa_no_canal(canal_id, ignorar_msg_id=None):
    """Ha alguma ficha viva neste ticket? Olha a analise em andamento E a fila
    duravel. So checar a analise nao bastava: com abertura agendada ou servidor
    offline a ficha fica na fila, e o jogador conseguia mandar outra por cima."""
    if canal_tem_ficha_em_analise(canal_id):
        return True
    return any(
        p.get("canal_id") == canal_id and p.get("msg_id") != ignorar_msg_id
        for p in carregar_fila_registro()
    )

def manter_apenas_ficha_mais_recente(canal_id=None):
    """Um ticket = uma ficha. Se houver mais de uma na fila do mesmo canal,
    vale a ULTIMA enviada e as anteriores sao descartadas.

    O id de mensagem do Discord e um snowflake crescente, entao o maior id e
    sempre o mais recente. Serve para limpar tickets em que o jogador mandou
    ficha duas vezes antes desta trava existir."""
    fila = carregar_fila_registro()
    if not fila:
        return []

    mais_recente = {}
    for entrada in fila:
        canal = entrada.get("canal_id")
        if canal_id is not None and canal != canal_id:
            continue
        atual = mais_recente.get(canal)
        if atual is None or int(entrada.get("msg_id") or 0) > int(atual.get("msg_id") or 0):
            mais_recente[canal] = entrada

    descartadas = []
    nova_fila = []
    for entrada in fila:
        canal = entrada.get("canal_id")
        if canal in mais_recente and entrada is not mais_recente[canal]:
            descartadas.append(entrada)
        else:
            nova_fila.append(entrada)

    if descartadas:
        salvar_fila_registro(nova_fila)
        for entrada in descartadas:
            print(f"[FICHAS] Ficha duplicada descartada no canal {entrada.get('canal_id')} "
                  f"(msg {entrada.get('msg_id')}); vale a mais recente.")
    return descartadas

def senha_ficha_valida(senha):
    """O login do Project Zomboid so aceita ASCII. Atencao: str.isalnum() sozinho
    aprova 'senhá123', porque acento conta como alfanumerico em Unicode; por isso
    o isascii() vem junto."""
    return bool(senha) and senha.isascii() and senha.isalnum()

def validar_campos_ficha(nome, senha):
    """Validacoes baratas feitas na hora do envio, antes de abrir os 3 minutos
    de analise. Devolve a mensagem de erro ou None se estiver tudo certo."""
    nome_limpo = remover_acentos(nome)

    if not nome_limpo:
        return "O campo **Nome/Sobrenome** não pode ficar vazio."
    if not re.match(r'^[a-zA-Z0-9_ ]+$', nome_limpo):
        return "O **nome** não pode conter aspas ou símbolos. Use apenas letras, números, espaço e `_`."
    if not senha:
        return "O campo **Senha** não pode ficar vazio."
    if not senha_ficha_valida(senha):
        return "A **senha** não pode ter símbolos, espaços ou acentos. Use apenas letras e números simples."

    return None

class FichaModal(discord.ui.Modal, title="Ficha de Personagem"):
    nome = discord.ui.TextInput(
        label="Nome/Sobrenome do personagem",
        placeholder="Ex: Joao Ferreira",
        max_length=60,
        required=True,
    )
    senha = discord.ui.TextInput(
        label="Senha para entrar no servidor",
        placeholder="Apenas letras e numeros, sem simbolos",
        max_length=40,
        required=True,
    )
    profissao = discord.ui.TextInput(
        label="Profissão do personagem",
        placeholder="Ex: Mecanico, Enfermeira, Policial...",
        max_length=80,
        required=True,
    )
    historia = discord.ui.TextInput(
        label="História do personagem",
        style=discord.TextStyle.paragraph,
        placeholder="Conte a origem e a trajetoria do seu personagem.",
        max_length=3000,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # O acento sai aqui (o login do jogo nao aceita) para o resumo mostrado
        # no ticket ser exatamente o login que sera criado no servidor.
        nome = remover_acentos(normalizar_campo_modal(str(self.nome)))
        senha = normalizar_campo_modal(str(self.senha))
        profissao = normalizar_campo_modal(str(self.profissao))
        historia = normalizar_campo_modal(str(self.historia), multilinha=True)

        erro = validar_campos_ficha(nome, senha)
        if erro:
            return await interaction.followup.send(f"❌ **Ficha não enviada:** {erro}\n\nClique no botão novamente e corrija.", ephemeral=True)

        if ficha_ativa_no_canal(interaction.channel.id):
            return await interaction.followup.send(
                "🚫 **Você já enviou uma ficha neste ticket.**\n\n"
                "Só é permitida **uma ficha por ticket**. Se errou algum dado, use o botão "
                "**🗑 Fechar Ticket** aqui embaixo e abra um novo — isso **não gasta vida**.",
                ephemeral=True,
            )

        user_id_str = str(interaction.user.id)
        tem_personagem = bool(carregar_personagens().get(user_id_str))
        pode_criar, vidas = jogador_pode_criar_personagem(user_id_str, tem_personagem)
        if not pode_criar:
            return await interaction.followup.send(
                f"💀 **Vidas esgotadas.** Você já usou todas as suas **{vidas['total']}** vidas desta temporada "
                f"e não pode criar outro personagem. Fale com a staff neste ticket.",
                ephemeral=True,
            )

        # A senha NAO vai no resumo publico: fica so no arquivo de controle
        # e na DM de confirmacao no final do registro.
        embed = discord.Embed(
            title="📋 Ficha Recebida",
            description=f"Ficha enviada por {interaction.user.mention} pelo formulário.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Nome/Sobrenome", value=f"```{nome}```", inline=False)
        embed.add_field(name="Profissão", value=f"```{profissao or 'Não informada'}```", inline=False)
        embed.add_field(name="História", value=formatar_texto_registro_embed(historia, padrao="Não informada"), inline=False)
        embed.set_footer(text="Senha recebida em segurança (não exibida no ticket).")

        ancora = await interaction.channel.send(embed=embed)

        ficha = FichaSubmetida(
            conteudo=montar_texto_ficha(nome, senha, profissao, historia),
            autor=interaction.user,
            canal=interaction.channel,
            guild=interaction.guild,
            ancora_id=ancora.id,
        )

        if not agendar_processamento_ficha(ficha):
            return await interaction.followup.send("⏳ Sua ficha já está sendo processada.", ephemeral=True)

        await interaction.followup.send("✅ **Ficha enviada!** Acompanhe o resultado aqui no ticket.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(f"[FICHAS] Erro no modal da ficha: {error}")
        mensagem = "❌ Não consegui processar sua ficha agora. Tente novamente em instantes."
        with suppress(Exception):
            if interaction.response.is_done():
                await interaction.followup.send(mensagem, ephemeral=True)
            else:
                await interaction.response.send_message(mensagem, ephemeral=True)

aviso_formato_antigo_em = {}
INTERVALO_AVISO_FORMATO_ANTIGO = 60

async def avisar_ficha_formato_antigo(canal, membro):
    """Ficha digitada no chat nao vale mais. Explica e devolve o botao.
    Com cooldown: quem colar a ficha varias vezes nao recebe uma parede de avisos."""
    agora = time.monotonic()
    ultimo = aviso_formato_antigo_em.get(canal.id, 0)
    if agora - ultimo < INTERVALO_AVISO_FORMATO_ANTIGO:
        return
    aviso_formato_antigo_em[canal.id] = agora

    with suppress(Exception):
        await canal.send(
            f"🚫 {membro.mention}, **fichas digitadas no chat não são mais aceitas.**\n\n"
            "Use o botão **📝 Preencher Ficha do Personagem** abaixo. Ele abre um formulário "
            "com os campos separados, então não tem como errar o formato.\n"
            "*O que você escreveu aqui foi ignorado — nada foi registrado e nenhuma vida foi gasta.*"
        )
    with suppress(Exception):
        await enviar_painel_ficha(canal, membro)

async def descartar_fichas_formato_antigo():
    """Remove da fila as fichas que entraram digitadas no chat, antes do formato
    antigo ser bloqueado. Ficha do Modal guarda conteudo_ficha; a digitada nao.
    Cada jogador afetado e avisado no proprio ticket para refazer pelo botao."""
    antigas = [
        p for p in carregar_fila_registro()
        if not (p.get("conteudo_ficha") or "").strip()
    ]
    if not antigas:
        return 0

    removidas = 0
    for entrada in antigas:
        canal_id = entrada.get("canal_id")
        with suppress(Exception):
            await cancelar_processamento_ficha(canal_id, entrada.get("msg_id"))
        if remover_da_fila_registro(canal_id, entrada.get("msg_id")):
            removidas += 1

        canal = bot.get_channel(canal_id) if canal_id else None
        if not canal:
            continue

        membro = None
        with suppress(Exception):
            membro = canal.guild.get_member(entrada.get("autor_id")) if canal.guild else None
        with suppress(Exception):
            await canal.send(
                f"⚠ {membro.mention if membro else 'Atenção'}, sua ficha foi enviada **digitada no chat**, "
                "formato que não é mais aceito.\n\n"
                "Ela **não foi registrada** e **não gastou vida**. "
                "Reenvie pelo botão **📝 Preencher Ficha do Personagem** abaixo."
            )
        if membro:
            with suppress(Exception):
                await enviar_painel_ficha(canal, membro)

    print(f"[FICHAS] {removidas} ficha(s) no formato antigo removida(s) da fila.")
    return removidas

async def enviar_painel_ficha(canal, membro):
    """Mensagem de abertura do ticket de personagem: ja avisa quantas vidas o
    jogador tem e so mostra o botao se ele ainda puder criar."""
    user_id_str = str(membro.id)
    tem_personagem = bool(carregar_personagens().get(user_id_str))
    pode_criar, vidas = jogador_pode_criar_personagem(user_id_str, tem_personagem)

    if not vidas["ilimitado"]:
        if not tem_personagem:
            situacao = (
                f"❤ **Vidas desta temporada:** `{vidas['total']}`\n"
                f"Este é o seu **primeiro personagem** — ele não gasta vida. "
                f"Depois dele, você poderá recriar mais **{vidas['total']}** vez(es)."
            )
        else:
            plural = "vida" if vidas["restantes"] == 1 else "vidas"
            situacao = (
                f"❤ **Vidas restantes:** `{vidas['restantes']}` {plural}\n"
                f"*(já usou {vidas['usadas']} de {vidas['total']})*"
            )
    else:
        situacao = "♾ **Vidas ilimitadas** nesta temporada."

    if not pode_criar:
        embed = discord.Embed(
            title="💀 Vidas Esgotadas",
            description=(
                f"{membro.mention}, você já usou todas as suas **{vidas['total']}** vidas desta temporada "
                f"e não pode criar outro personagem.\n\n"
                f"Se achar que houve engano, aguarde o atendimento da staff aqui neste ticket."
            ),
            color=discord.Color.red(),
        )
        embed.set_footer(text="Staff: use /adicionar_vidas para liberar uma vida extra.")
        return await canal.send(embed=embed, view=FecharTicketView())

    aviso_abertura = ""
    if not registros_estao_liberados():
        aviso_abertura = (
            f"\n\n{texto_abertura_discord()}\n"
            "Pode preencher sua ficha **agora mesmo** — ela fica guardada e seu personagem "
            "é criado automaticamente na hora marcada."
        )

    return await canal.send(
        f"{situacao}{aviso_abertura}\n\n"
        "📝 **Clique no botão abaixo para preencher sua ficha.**\n"
        "O formulário abre uma janela com os campos separados — assim não tem risco de errar o formato.\n"
        "*(Se preferir, você ainda pode digitar a ficha normalmente aqui no chat.)*",
        view=FichaFormView(),
    )

class FichaFormView(discord.ui.View):
    """View persistente: continua funcionando depois de reiniciar o bot."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Preencher Ficha do Personagem",
        style=discord.ButtonStyle.success,
        emoji="📝",
        custom_id="btn_preencher_ficha_zomboid",
    )
    async def preencher_ficha(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FichaModal())

    @discord.ui.button(
        label="Fechar Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🗑",
        custom_id="btn_fechar_ticket_zomboid",
    )
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await fechar_ticket_por_botao(interaction)

class FecharTicketView(discord.ui.View):
    """So o botao de fechar. Usada quando o jogador nao pode mais criar ficha."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🗑",
        custom_id="btn_fechar_ticket_solo",
    )
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await fechar_ticket_por_botao(interaction)

PREFIXO_CANAL_TICKET = "ticket-"

def canal_e_ticket(canal):
    """Trava de seguranca do botao de fechar: ele e persistente e poderia ser
    acionado numa mensagem antiga fora de um ticket. So apagamos canal cujo nome
    segue o padrao dos tickets, ou que esteja numa categoria de ticket."""
    nome = getattr(canal, "name", "") or ""
    if nome.lower().startswith(PREFIXO_CANAL_TICKET):
        return True

    categoria = getattr(canal, "category", None)
    if not categoria:
        return False
    if categoria_processa_ficha_pos_morte(categoria):
        return True

    categorias_paineis = {
        normalizar_chave_personagem(cfg.get("categoria", ""))
        for cfg in carregar_paineis().values()
        if isinstance(cfg, dict)
    }
    return normalizar_chave_personagem(categoria.name) in categorias_paineis

async def fechar_ticket_por_botao(interaction: discord.Interaction):
    """Fecha o ticket a pedido do jogador.

    Descarta a ficha que estava guardada, para ela nao ser registrada depois.
    Como a vida so e consumida quando o registro e CONFIRMADO no servidor,
    fechar aqui nunca gasta vida."""
    try:
        await interaction.response.defer(ephemeral=True, thinking=True)
    except discord.HTTPException:
        return

    canal = interaction.channel
    if not canal_e_ticket(canal):
        return await interaction.followup.send(
            "❌ Este botão só funciona dentro de um ticket.", ephemeral=True)

    with suppress(Exception):
        await cancelar_processamento_ficha(canal.id, None)

    descartadas = 0
    for entrada in [p for p in carregar_fila_registro() if p.get("canal_id") == canal.id]:
        with suppress(Exception):
            await cancelar_processamento_ficha(entrada.get("canal_id"), entrada.get("msg_id"))
        if remover_da_fila_registro(entrada.get("canal_id"), entrada.get("msg_id")):
            descartadas += 1

    for analise in [a for a in carregar_fichas_em_analise() if a.get("canal_id") == canal.id]:
        with suppress(Exception):
            await cancelar_processamento_ficha(analise.get("canal_id"), analise.get("msg_id"))
        remover_ficha_em_analise(analise.get("canal_id"), analise.get("msg_id"))

    cancelar_fechamento_ticket(canal.id)

    print(f"[TICKET] {interaction.user} fechou o ticket {canal.id}; {descartadas} ficha(s) descartada(s).")
    await interaction.followup.send("✅ Fechando o ticket... Pode abrir um novo quando quiser.", ephemeral=True)

    with suppress(Exception):
        await canal.send(
            f"🗑 **Ticket fechado por {interaction.user.mention}.**\n"
            + ("A ficha enviada foi **descartada** e **não gastou vida**.\n" if descartadas else "")
            + "Este canal será apagado em instantes."
        )

    await asyncio.sleep(5)
    with suppress(Exception):
        await canal.delete(reason=f"Ticket fechado por {interaction.user}")

@dataclass
class RconResult:
    ok: bool
    output: str = ""
    error: str = ""
    attempts: int = 0
    empty_response: bool = False

class RconSessionManager:
    def __init__(self, host, port, password):
        self.host = host
        self.port = int(port)
        self.password = password
        self.frag_threshold = 4096
        self._reader = None
        self._writer = None
        self._lock = None
        self._connected_at = 0.0
        self._last_success_at = 0.0
        self._last_error = ""

    def _get_lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _esta_conectado(self):
        return self._writer is not None and not self._writer.is_closing()

    def _sessao_expirada(self):
        return self._connected_at and (time.monotonic() - self._connected_at) >= RCON_SESSION_TTL

    def teve_sucesso_recente(self):
        if not self._last_success_at:
            return False
        return (time.monotonic() - self._last_success_at) <= RCON_RECENT_SUCCESS_WINDOW

    @property
    def ultimo_erro(self):
        return self._last_error

    def _configurar_socket(self):
        if not self._writer:
            return

        sock = self._writer.get_extra_info("socket")
        if not sock:
            return

        with suppress(OSError, AttributeError):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        with suppress(OSError, AttributeError):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        with suppress(OSError, AttributeError):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        with suppress(OSError, AttributeError):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        with suppress(OSError, AttributeError):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

    async def _fechar_locked(self):
        writer = self._writer
        self._reader = None
        self._writer = None
        self._connected_at = 0.0

        if writer is None:
            return

        writer.close()
        with suppress(Exception):
            await writer.wait_closed()

    async def close(self):
        async with self._get_lock():
            await self._fechar_locked()

    async def _send_packet_locked(self, packet):
        if not self._writer:
            raise ConnectionError("Socket RCON indisponível.")

        self._writer.write(bytes(packet))
        await asyncio.wait_for(self._writer.drain(), timeout=RCON_COMMAND_TIMEOUT)

    async def _read_packet_locked(self, timeout):
        if not self._reader:
            raise ConnectionError("Leitor RCON indisponível.")
        return await asyncio.wait_for(Packet.aread(self._reader), timeout=timeout)

    async def _autenticar_locked(self):
        if not self.password:
            raise ValueError("RCON_PASSWORD não configurado no .env.")

        await self._send_packet_locked(Packet.make_login(self.password, encoding="utf-8"))

        for _ in range(8):
            resposta = await self._read_packet_locked(RCON_COMMAND_TIMEOUT)
            if resposta.type == Type.SERVERDATA_AUTH_RESPONSE:
                if resposta.id == -1:
                    raise WrongPassword()
                return

        raise SessionTimeout("Autenticação RCON sem resposta final do servidor.")

    async def _garantir_conexao_locked(self):
        if self._esta_conectado() and not self._sessao_expirada():
            return

        await self._fechar_locked()

        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=RCON_CONNECT_TIMEOUT
        )
        self._connected_at = time.monotonic()
        self._configurar_socket()

        try:
            await self._autenticar_locked()
        except Exception:
            await self._fechar_locked()
            raise

    async def _executar_locked(self, comando):
        requisicao = Packet.make_command(comando, encoding="utf-8")
        await self._send_packet_locked(requisicao)
        resposta = await self._read_packet_locked(RCON_COMMAND_TIMEOUT)

        if len(resposta.payload) >= self.frag_threshold:
            await self._send_packet_locked(Packet.make_empty_response())
            while True:
                sucessor = await self._read_packet_locked(RCON_COMMAND_TIMEOUT)
                if sucessor.id != resposta.id:
                    break
                resposta += sucessor

        if resposta.id != requisicao.id:
            raise SessionTimeout("Sessão RCON perdeu sincronização entre requisição e resposta.")

        return resposta.payload.decode("utf-8", errors="replace").strip()

    def _traduzir_erro(self, erro):
        if isinstance(erro, asyncio.TimeoutError):
            return f"timeout aguardando resposta do RCON ({RCON_COMMAND_TIMEOUT:.0f}s)"
        if isinstance(erro, ConnectionRefusedError):
            return "conexão recusada pelo host/porta RCON"
        if isinstance(erro, EmptyResponse):
            return "o servidor fechou o socket sem responder"
        if isinstance(erro, asyncio.IncompleteReadError):
            return "resposta RCON truncada antes do fim"
        if isinstance(erro, SessionTimeout):
            return str(erro) or "sessão RCON expirada/desalinhada"
        if isinstance(erro, WrongPassword):
            return "senha RCON rejeitada pelo servidor"
        if isinstance(erro, OSError):
            return str(erro) or erro.__class__.__name__
        return str(erro) or erro.__class__.__name__

    async def execute(self, comando):
        async with self._get_lock():
            for tentativa in range(1, RCON_MAX_TENTATIVAS + 1):
                try:
                    await self._garantir_conexao_locked()
                    resposta = await self._executar_locked(comando)
                    self._last_success_at = time.monotonic()
                    self._last_error = ""
                    return RconResult(
                        ok=True,
                        output=resposta,
                        attempts=tentativa,
                        empty_response=(resposta == "")
                    )
                except WrongPassword as erro:
                    self._last_error = self._traduzir_erro(erro)
                    await self._fechar_locked()
                    return RconResult(ok=False, error=self._last_error, attempts=tentativa)
                except (asyncio.TimeoutError, EmptyResponse, SessionTimeout, asyncio.IncompleteReadError, OSError, ConnectionError) as erro:
                    self._last_error = self._traduzir_erro(erro)
                    await self._fechar_locked()
                    if tentativa >= RCON_MAX_TENTATIVAS:
                        return RconResult(ok=False, error=self._last_error, attempts=tentativa)
                    await asyncio.sleep(min(RCON_RETRY_DELAY * tentativa, 5))
                except Exception as erro:
                    self._last_error = self._traduzir_erro(erro)
                    await self._fechar_locked()
                    if tentativa >= RCON_MAX_TENTATIVAS:
                        return RconResult(ok=False, error=self._last_error, attempts=tentativa)
                    await asyncio.sleep(min(RCON_RETRY_DELAY * tentativa, 5))

rcon_manager = RconSessionManager(RCON_IP, RCON_PORT, RCON_PASSWORD)

async def checar_porta_rcon():
    writer = None
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(RCON_IP, int(RCON_PORT)),
            timeout=RCON_CONNECT_TIMEOUT
        )
        return True
    except Exception:
        return False
    finally:
        if writer is not None:
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()

def mensagem_parece_status_servidor(mensagem):
    if mensagem.author != bot.user or not mensagem.embeds:
        return False

    titulo = mensagem.embeds[0].title or ""
    return titulo.startswith("Servidor Online") or titulo.startswith("Servidor Offline")

async def encontrar_mensagem_status_existente(canal_status):
    encontrada = None
    duplicadas = []

    async for mensagem in canal_status.history(limit=100):
        if not mensagem_parece_status_servidor(mensagem):
            continue

        if encontrada is None:
            encontrada = mensagem
        else:
            duplicadas.append(mensagem)

    for mensagem in duplicadas:
        with suppress(Exception):
            await mensagem.delete()

    return encontrada

LIMITE_CANAIS_POR_CATEGORIA = 50   # limite rigido do Discord
LIMITE_CANAIS_POR_SERVIDOR = 500   # limite rigido do Discord

def categorias_da_familia(guild, nome_base):
    """A categoria principal e as de transbordo ('NOME 2', 'NOME 3'...)."""
    alvo = normalizar_chave_personagem(nome_base)
    familia = []
    for categoria in guild.categories:
        nome = normalizar_chave_personagem(categoria.name)
        if nome == alvo or re.fullmatch(rf"{re.escape(alvo)} \d+", nome or ""):
            familia.append(categoria)
    familia.sort(key=lambda c: len(c.name))
    return familia

def ticket_existente_do_jogador(guild, nome_base, nome_canal):
    """Procura o ticket do jogador em TODAS as categorias da familia, nao so na
    principal: com transbordo o ticket antigo pode estar numa das extras."""
    for categoria in categorias_da_familia(guild, nome_base):
        canal = discord.utils.get(categoria.text_channels, name=nome_canal)
        if canal:
            return canal
    return None

async def obter_categoria_com_espaco(guild, nome_base):
    """O Discord permite no maximo 50 canais por categoria. Quando a categoria de
    tickets enche, TODA criacao passa a falhar - e foi isso que derrubou a
    abertura de tickets. Aqui achamos (ou criamos) uma categoria com espaco.

    Devolve (categoria, erro_para_o_jogador)."""
    familia = categorias_da_familia(guild, nome_base)

    for categoria in familia:
        if len(categoria.channels) < LIMITE_CANAIS_POR_CATEGORIA:
            return categoria, None

    if len(guild.channels) >= LIMITE_CANAIS_POR_SERVIDOR - 1:
        return None, ("❌ O servidor atingiu o limite de canais do Discord "
                      f"({LIMITE_CANAIS_POR_SERVIDOR}). A staff precisa apagar canais antigos.")

    # Todas cheias: cria a proxima da familia.
    proximo = len(familia) + 1 if familia else 1
    nome_novo = nome_base if proximo == 1 else f"{nome_base} {proximo}"
    try:
        categoria = await guild.create_category(nome_novo)
        if familia:
            print(f"[TICKET] Categoria '{nome_base}' cheia ({LIMITE_CANAIS_POR_CATEGORIA} canais); "
                  f"criada '{nome_novo}' para continuar aceitando tickets.")
        else:
            print(f"[TICKET] Categoria '{nome_novo}' nao existia; criada agora.")
        return categoria, None
    except discord.Forbidden:
        return None, "❌ A categoria de tickets está cheia e não tenho permissão para criar outra. Avise a staff."
    except discord.HTTPException as erro:
        print(f"[TICKET] Falha ao criar categoria de transbordo: {erro}")
        return None, "❌ A categoria de tickets está cheia e não consegui criar outra. Avise a staff."

class TicketButton(discord.ui.View):
    def __init__(self, texto_botao="Abrir Ticket", emoji_botao="📩"):
        super().__init__(timeout=None)
        botao = discord.ui.Button(label=texto_botao, style=discord.ButtonStyle.secondary, emoji=emoji_botao, custom_id="btn_abrir_ticket_zomboid")
        botao.callback = self.abrir_ticket_btn
        self.add_item(botao)

    async def abrir_ticket_btn(self, interaction: discord.Interaction):
        # O Discord exige resposta em ate 3 segundos. Criar categoria e canal
        # sao das chamadas mais limitadas por rate limit: com varios jogadores
        # clicando ao mesmo tempo isso passa de 3s e o botao falha. O defer
        # reserva a interacao antes de comecar o trabalho pesado.
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
        except discord.HTTPException:
            return

        paineis = carregar_paineis()
        msg_id = str(interaction.message.id)
        config = paineis.get(msg_id, {"categoria": " 🎫 ATENDIMENTO", "mensagem": "Nossa equipe já foi notificada. Por favor, mande suas informações."})

        nome_categoria = config["categoria"]
        texto_msg = config["mensagem"]

        guild = interaction.guild
        nome_canal = f"ticket-{interaction.user.name.lower()}"

        # Ticket ja aberto (em qualquer categoria da familia).
        canal_existente = ticket_existente_do_jogador(guild, nome_categoria, nome_canal)
        if canal_existente:
            return await interaction.followup.send(
                f"Você já tem um ticket aberto: {canal_existente.mention}.", ephemeral=True)

        categoria, erro_categoria = await obter_categoria_com_espaco(guild, nome_categoria)
        if erro_categoria:
            return await interaction.followup.send(erro_categoria, ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        try:
            canal_ticket = await guild.create_text_channel(nome_canal, category=categoria, overwrites=overwrites)
        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ Não tenho permissão para criar o canal do ticket. Avise a staff.", ephemeral=True)
        except discord.HTTPException as erro:
            # Ultima tentativa: se a categoria encheu entre a checagem e agora,
            # abre uma nova de transbordo e tenta de novo.
            print(f"[TICKET] Falha ao criar canal para {interaction.user} "
                  f"(codigo {getattr(erro, 'code', '?')}): {erro}")
            categoria, erro_categoria = await obter_categoria_com_espaco(guild, nome_categoria)
            if erro_categoria:
                return await interaction.followup.send(erro_categoria, ephemeral=True)
            try:
                canal_ticket = await guild.create_text_channel(nome_canal, category=categoria, overwrites=overwrites)
            except discord.HTTPException as erro2:
                print(f"[TICKET] Segunda tentativa falhou (codigo {getattr(erro2, 'code', '?')}): {erro2}")
                return await interaction.followup.send(
                    "❌ Não consegui abrir seu ticket agora.\n"
                    f"*Detalhe para a staff: código `{getattr(erro2, 'code', '?')}` — {erro2}*",
                    ephemeral=True,
                )

        await interaction.followup.send(f"✅ Seu ticket foi aberto: {canal_ticket.mention}", ephemeral=True)
        await canal_ticket.send(f"👋 **Olá, {interaction.user.mention}!**\n\n{texto_msg}\n\n*(Staff: Use `/fechar_ticket`)*")

        with suppress(Exception):
            if categoria_processa_ficha_pos_morte(categoria):
                # Ticket de personagem: o painel da ficha ja traz o botao de fechar.
                await enviar_painel_ficha(canal_ticket, interaction.user)
            else:
                await canal_ticket.send(
                    "🗑 **Terminou seu atendimento?** Use o botão abaixo para fechar este ticket.\n"
                    "*Se ainda precisa de ajuda, é só continuar conversando aqui.*",
                    view=FecharTicketView(),
                )

class ZomboidBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.voice_states = True
        intents.reactions = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(TicketButton())
        self.add_view(FichaFormView())
        self.add_view(FecharTicketView())
        await self.tree.sync()

    async def close(self):
        tarefas = [tarefa for tarefa in [
            tarefa_monitor_mortes,
            tarefa_monitor_eventos,
            tarefa_monitor_call_ingame,
            tarefa_varredura_fichas,
            tarefa_retomar_analises,
            tarefa_fichas_pendentes,
            *tarefas_remocao_vip.values(),
            *tarefas_fichas,
        ] if tarefa is not None]
        for loop in (radar_servidor, loop_sorteios, loop_retentar_registros, supervisor_monitores, loop_fechar_tickets):
            if loop.is_running():
                loop.cancel()
        for tarefa in tarefas:
            if tarefa and not tarefa.done():
                tarefa.cancel()
        if tarefas:
            await asyncio.gather(*tarefas, return_exceptions=True)

        for sessao in list(gravadores.values()):
            with suppress(Exception):
                sessao.sink.cleanup()
            with suppress(Exception):
                if os.path.exists(sessao.arquivo_wav):
                    os.remove(sessao.arquivo_wav)
        gravadores.clear()

        for guild in self.guilds:
            vc = guild.voice_client
            if vc and vc.is_connected():
                with suppress(Exception):
                    if getattr(vc, "is_listening", lambda: False)():
                        vc.stop_listening()
                    await vc.disconnect()

        manager = globals().get("rcon_manager")
        if manager:
            await manager.close()
        await super().close()

bot = ZomboidBot()

@bot.command(name="deploy")
@commands.has_permissions(administrator=True)
async def deploy(ctx):
    await ctx.send(" **Iniciando Deploy...** Sincronizando comandos Slash com o Discord...")
    synced = await bot.tree.sync()
    await ctx.send(f"✅ **Deploy Concluído!** {len(synced)} comandos ativados.")

async def bloquear_se_nao_for_staff(interaction: discord.Interaction):
    """Trava em tempo de execucao. O default_permissions do Discord pode ser
    afrouxado por um admin nas Integracoes do servidor; esta checagem garante
    que um jogador comum nunca dispare comandos que consomem API."""
    if usuario_e_staff(interaction.user):
        return False

    mensagem = "🚫 Este comando é de uso exclusivo da staff."
    if interaction.response.is_done():
        await interaction.followup.send(mensagem, ephemeral=True)
    else:
        await interaction.response.send_message(mensagem, ephemeral=True)
    return True

@bot.tree.command(name="entrar_voz", description="🎙 Faz o bot entrar na sua call atual")
@app_commands.default_permissions(administrator=True)
async def entrar_voz(interaction: discord.Interaction):
    if await bloquear_se_nao_for_staff(interaction):
        return
    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.response.send_message("❌ Você precisa estar em uma call para eu entrar.", ephemeral=True)

    try:
        vc, erro = await conectar_bot_na_call_do_autor(interaction.user)
        if erro:
            return await interaction.response.send_message(erro, ephemeral=True)
        await interaction.response.send_message(f"👂 Conectado em {vc.channel.mention}.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Não consegui entrar na call: {e}", ephemeral=True)

@bot.tree.command(name="iniciar_reuniao", description="🔴 Entra na sua call e começa a gravar a reunião")
@app_commands.default_permissions(administrator=True)
async def iniciar_reuniao(interaction: discord.Interaction):
    if await bloquear_se_nao_for_staff(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    ok, resposta = await iniciar_gravacao_reuniao(interaction.user, interaction.channel)
    await interaction.followup.send(resposta, ephemeral=True)

@bot.tree.command(name="encerrar_reuniao", description="📋 Para a gravação da reunião e gera a ata resumida")
@app_commands.default_permissions(administrator=True)
async def encerrar_reuniao(interaction: discord.Interaction):
    if await bloquear_se_nao_for_staff(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    _, resposta = await encerrar_gravacao_reuniao(interaction.guild, interaction.channel)
    if resposta == "ok":
        await interaction.followup.send("✅ Gravação encerrada. A ata foi enviada no canal.", ephemeral=True)
    elif resposta == "audio_curto":
        await interaction.followup.send("⚠ A gravação foi encerrada, mas o áudio ficou curto ou vazio demais para uma ata confiável.", ephemeral=True)
    else:
        await interaction.followup.send(resposta if isinstance(resposta, str) else "❌ Não consegui encerrar a reunião.", ephemeral=True)

def agendar_remocao_vip_unica(guild_id, user_id, cargo_id, canal_id, segundos_espera, chave_vip, vencimento_esperado):
    tarefa_anterior = tarefas_remocao_vip.get(chave_vip)
    if tarefa_anterior and tarefa_anterior is not asyncio.current_task() and not tarefa_anterior.done():
        tarefa_anterior.cancel()

    tarefa = bot.loop.create_task(
        agendar_remocao_vip(
            guild_id, user_id, cargo_id, canal_id, segundos_espera,
            chave_vip, vencimento_esperado,
        ),
        name=f"remover-vip-{chave_vip}",
    )
    tarefas_remocao_vip[chave_vip] = tarefa
    return tarefa

@tasks.loop(seconds=20)
async def loop_sorteios():
    sorteios = carregar_sorteios()
    agora = datetime.now()
    terminados = []

    for msg_id, dados in sorteios.items():
        fim = datetime.fromisoformat(dados["fim"])
        if agora >= fim:
            terminados.append(msg_id)
            try:
                guild = bot.get_guild(dados["guild_id"])
                if not guild: continue
                canal = guild.get_channel(dados["canal_id"])
                if not canal: continue
                
                try:
                    msg = await canal.fetch_message(int(msg_id))
                except discord.NotFound:
                    continue 

                reacao_oficial = None
                for r in msg.reactions:
                    if str(r.emoji) == dados["emoji"]:
                        reacao_oficial = r
                        break
                
                if not reacao_oficial:
                    await canal.send(f" O sorteio **{dados['titulo']}** terminou, mas não consegui achar a reação oficial.")
                    continue

                participantes = [user async for user in reacao_oficial.users()]
                participantes = participantes_elegiveis_sorteio(guild, participantes)
                
                if not participantes:
                    await canal.send(f"😢 O sorteio **{dados['titulo']}** encerrou, mas ninguém participou!")
                else:
                    ganhador = random.choice(participantes)
                    await canal.send(f"🎉 **PARABÉNS** {ganhador.mention}! Você ganhou o sorteio: **{dados['titulo']}**!")

                    if dados["cargo_id"]:
                        cargo = guild.get_role(dados["cargo_id"])
                        if cargo:
                            try:
                                await ganhador.add_roles(cargo)
                                qt_dias = 30
                                vencimento = datetime.now() + timedelta(days=qt_dias)
                                vips = carregar_vips()
                                chave_vip = f"{ganhador.id}_{cargo.id}_{canal.id}"
                                vips[chave_vip] = vencimento.isoformat()
                                salvar_vips(vips)
                                agendar_remocao_vip_unica(
                                    guild.id, ganhador.id, cargo.id, canal.id,
                                    qt_dias * 24 * 60 * 60, chave_vip, vencimento.isoformat(),
                                )
                                
                                canal_registro = discord.utils.get(guild.text_channels, name="registro-vips")
                                if canal_registro:
                                    embed_log = discord.Embed(title=" VIP Concedido via Sorteio!", color=discord.Color.gold())
                                    embed_log.add_field(name="Ganhador", value=ganhador.mention, inline=False)
                                    embed_log.add_field(name="Cargo", value=cargo.mention, inline=True)
                                    embed_log.add_field(name="Duração", value=f"{qt_dias} dias", inline=True)
                                    embed_log.add_field(name="Sorteio", value=dados['titulo'], inline=False)
                                    await canal_registro.send(embed=embed_log)
                            except discord.Forbidden:
                                await canal.send(f"⚠ {ganhador.mention} ganhou o sorteio, mas o Discord bloqueou a entrega do cargo **{cargo.name}**.")
            except Exception as e:
                print(f"Erro ao finalizar sorteio {msg_id}: {e}")

    if terminados:
        for t in terminados:
            del sorteios[t]
        salvar_sorteios(sorteios)

@tasks.loop(seconds=60)
async def radar_servidor():
    global servidor_online, falhas_rcon
    resultado = await enviar_comando_rcon_detalhado("players")
    porta_rcon_ativa = False
    rcon_degradado = False
    qtd_players = "?"

    if resultado.ok:
        match = re.search(r'Players connected \((\d+)\)', resultado.output, re.IGNORECASE)
        if match:
            qtd_players = match.group(1)
        falhas_rcon = 0
    else:
        falhas_rcon += 1
        porta_rcon_ativa = await checar_porta_rcon()
        rcon_degradado = porta_rcon_ativa or rcon_manager.teve_sucesso_recente()

    status_confirmado_online = resultado.ok or rcon_degradado

    if resultado.ok:
        servidor_online = True
        if carregar_pendentes() and not fila_pendentes_em_espera:
            agendar_processamento_fichas_pendentes()
    elif not status_confirmado_online and servidor_online and falhas_rcon >= RCON_FALHAS_OFFLINE:
        servidor_online = False

    canal_status = None
    if CANAL_STATUS_ID and CANAL_STATUS_ID.isdigit():
        canal_status = bot.get_channel(int(CANAL_STATUS_ID))

    if not canal_status:
        return

    hora_atual = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    if status_confirmado_online:
        cor = 0xf1c40f if (rcon_degradado and not resultado.ok) else 0x2ecc71
        titulo = "Servidor Online (RCON Instavel)" if (rcon_degradado and not resultado.ok) else "Servidor Online!"
        descricao = "O servidor Organic RP Zomboid esta operante."
        if rcon_degradado and not resultado.ok:
            descricao += f"\n\nRCON em oscilacao: `{resultado.error}`"
        descricao += f"\n\nJogadores Online: `{qtd_players}`"
        embed = discord.Embed(title=titulo, description=descricao, color=cor)
        embed.set_footer(text=f"Ultima verificacao: {hora_atual} | Falhas consecutivas de RCON: {falhas_rcon}")
    else:
        embed = discord.Embed(title="Servidor Offline!", description="O servidor Organic RP Zomboid caiu, esta reiniciando ou deixou de responder no RCON.", color=0xe74c3c)
        embed.set_footer(text=f"Ultima verificacao: {hora_atual} | Falhas consecutivas: {falhas_rcon}/{RCON_FALHAS_OFFLINE}")

    msg_id = carregar_msg_status()
    msg_status = None
    editado = False
    pular_publicacao_status = False

    if msg_id:
        try:
            msg_status = await canal_status.fetch_message(msg_id)
        except discord.NotFound:
            msg_status = None
        except Exception as erro:
            print(f"[STATUS] Falha ao buscar mensagem salva ({msg_id}); evitando duplicar status: {erro}")
            pular_publicacao_status = True

    if not msg_status and not pular_publicacao_status:
        try:
            msg_status = await encontrar_mensagem_status_existente(canal_status)
        except Exception as erro:
            print(f"[STATUS] Falha ao procurar status antigo; evitando criar duplicata: {erro}")
            pular_publicacao_status = True

    if msg_status and not pular_publicacao_status:
        try:
            await msg_status.edit(embed=embed)
            salvar_msg_status(msg_status.id)
            editado = True
        except discord.NotFound:
            editado = False
        except Exception as erro:
            print(f"[STATUS] Falha ao editar status existente; evitando duplicar status: {erro}")
            pular_publicacao_status = True

    if not editado and not pular_publicacao_status:
        nova_msg = await canal_status.send(embed=embed)
        salvar_msg_status(nova_msg.id)

def agendar_processamento_ficha(message, bypass=False, checar_online=True, segundos_espera=None, msg_espera_id=None):
    chave = (message.channel.id, message.id)
    if chave in fichas_em_processamento:
        return False

    fichas_em_processamento.add(chave)

    async def executar():
        try:
            await processar_registro_pos_morte(
                message,
                bypass=bypass,
                checar_online=checar_online,
                segundos_espera=segundos_espera,
                msg_espera_id=msg_espera_id,
            )
        except asyncio.CancelledError:
            raise
        except Exception as erro:
            print(f"[FICHAS] Erro inesperado ao processar {message.id}: {erro}")
        finally:
            fichas_em_processamento.discard(chave)
            tarefas_fichas_por_chave.pop(chave, None)

    tarefa = bot.loop.create_task(executar(), name=f"processar-ficha-{message.id}")
    tarefas_fichas.add(tarefa)
    tarefas_fichas_por_chave[chave] = tarefa
    tarefa.add_done_callback(tarefas_fichas.discard)
    return True

async def cancelar_processamento_ficha(canal_id, msg_id):
    """Interrompe uma analise em andamento (usado pelo /aprovar_ficha para nao
    ter que esperar os 3 minutos terminarem)."""
    chave = (canal_id, msg_id)
    tarefa = tarefas_fichas_por_chave.get(chave)

    if tarefa and not tarefa.done():
        tarefa.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await tarefa

    tarefas_fichas_por_chave.pop(chave, None)
    fichas_em_processamento.discard(chave)

@tasks.loop(seconds=30)
async def loop_fechar_tickets():
    """Fecha os tickets cujo prazo venceu. O prazo esta em disco, entao um
    reinicio no meio da espera nao deixa o canal orfao."""
    pendentes = carregar_tickets_para_fechar()
    if not pendentes:
        return

    agora = time.time()
    restantes = []

    for item in pendentes:
        try:
            if agora < float(item.get("fechar_em", 0)):
                restantes.append(item)
                continue

            canal = bot.get_channel(int(item.get("canal_id")))
            if canal:
                await canal.delete(reason="Registro concluido: fechamento automatico do ticket")
                print(f"[TICKET] Canal {item.get('canal_id')} fechado automaticamente.")
        except discord.NotFound:
            pass
        except Exception as erro:
            print(f"[TICKET] Falha ao fechar canal {item.get('canal_id')}: {erro}")

    if len(restantes) != len(pendentes):
        salvar_tickets_para_fechar(restantes)

@loop_fechar_tickets.before_loop
async def antes_loop_fechar_tickets():
    await bot.wait_until_ready()

@tasks.loop(minutes=2)
async def loop_retentar_registros():
    """Rede de seguranca independente: a cada 2 minutos reexamina a fila.
    Assim o registro nao depende de um unico gatilho ter funcionado."""
    if not servidor_online or fila_pendentes_em_espera:
        return
    if not aprovacao_automatica_ativa() or not registros_estao_liberados():
        return

    fila = carregar_fila_registro()
    if not fila:
        return

    ociosas = [
        p for p in fila
        if (p.get("canal_id"), p.get("msg_id")) not in fichas_em_processamento
        and p.get("tentativas", 0) < MAX_TENTATIVAS_REGISTRO
    ]
    if not ociosas:
        return

    print(f"[FICHAS] Retentativa automatica: {len(ociosas)} ficha(s) aguardando registro.")
    await processar_fichas_pendentes(espera_estabilizacao=False)

@loop_retentar_registros.before_loop
async def antes_loop_retentar_registros():
    await bot.wait_until_ready()

@tasks.loop(minutes=1)
async def supervisor_monitores():
    """Os monitores de morte e evento leem arquivo em loop infinito. Se um deles
    morrer por exceçao, o bot continua online mas para de detectar morte -- e o
    anti-fraude inteiro depende disso. Aqui eles sao ressuscitados."""
    global tarefa_monitor_mortes, tarefa_monitor_eventos, tarefa_monitor_call_ingame

    vigiados = [
        ("mortes", "tarefa_monitor_mortes", monitorar_mortes),
        ("eventos", "tarefa_monitor_eventos", monitorar_eventos),
        ("call in-game", "tarefa_monitor_call_ingame", monitorar_call_ingame),
    ]

    for rotulo, nome_global, funcao in vigiados:
        tarefa = globals().get(nome_global)

        if tarefa is None:
            continue
        if not tarefa.done():
            continue
        if tarefa.cancelled():
            continue  # desligado de proposito (shutdown)

        erro = tarefa.exception()
        if erro is None:
            # Terminou sem erro: o monitor esta desativado na config
            # (canal/caminho nao configurado). Reiniciar seria loop infinito.
            continue

        print(f"[SUPERVISOR] Monitor de {rotulo} caiu ({erro!r}). Reiniciando...")
        globals()[nome_global] = bot.loop.create_task(funcao(), name=f"monitor-{rotulo}")

@supervisor_monitores.before_loop
async def antes_supervisor_monitores():
    await bot.wait_until_ready()
    # Da tempo do on_ready criar os monitores antes da primeira checagem.
    await asyncio.sleep(30)

def agendar_processamento_fichas_pendentes():
    global tarefa_fichas_pendentes
    if tarefa_fichas_pendentes and not tarefa_fichas_pendentes.done():
        return tarefa_fichas_pendentes
    tarefa_fichas_pendentes = bot.loop.create_task(
        processar_fichas_pendentes(),
        name="processar-fichas-pendentes",
    )
    return tarefa_fichas_pendentes

async def registrar_log_vidas(membro, nome_personagem, vidas, primeiro_personagem):
    """Publica no canal de vidas cada personagem novo criado."""
    if not CANAL_VIDAS_ID:
        return

    canal = None
    with suppress(Exception):
        canal = bot.get_channel(int(CANAL_VIDAS_ID))
    if not canal:
        print(f"[VIDAS] Canal {CANAL_VIDAS_ID} nao encontrado; log nao publicado.")
        return

    if vidas["ilimitado"]:
        restantes_txt = "♾ Ilimitadas"
        cor = discord.Color.blurple()
    elif vidas["restantes"] <= 0:
        restantes_txt = "💀 **0** — era a última vida"
        cor = discord.Color.red()
    else:
        plural = "vida" if vidas["restantes"] == 1 else "vidas"
        restantes_txt = f"❤ **{vidas['restantes']}** {plural}"
        cor = discord.Color.green() if vidas["restantes"] > 1 else discord.Color.orange()

    titulo = "🆕 Primeiro Personagem da Temporada" if primeiro_personagem else "🔁 Personagem Recriado"
    embed = discord.Embed(title=titulo, color=cor)
    embed.add_field(name="Jogador", value=f"{membro.mention}\n`{membro.display_name}`", inline=False)
    embed.add_field(name="Personagem", value=f"```{nome_personagem}```", inline=False)
    embed.add_field(name="Vidas restantes", value=restantes_txt, inline=True)

    if not vidas["ilimitado"]:
        embed.add_field(name="Já usadas", value=f"`{vidas['usadas']}` de `{vidas['total']}`", inline=True)
        if vidas["extras"]:
            embed.add_field(name="Bônus da staff", value=f"`{vidas['extras']:+d}`", inline=True)

    embed.set_footer(text=f"Discord ID: {membro.id}")
    with suppress(Exception):
        await canal.send(embed=embed)

async def alertar_staff_ficha_travada(canal, entrada):
    """Ficha que estourou o limite de tentativas nunca e descartada: vira aviso
    para a staff resolver na mao com /aprovar_ficha."""
    if entrada.get("alertou_staff"):
        return

    atualizar_entrada_fila(entrada["canal_id"], entrada["msg_id"], alertou_staff=True)
    with suppress(Exception):
        await canal.send(
            f"🚨 **ATENÇÃO STAFF:** esta ficha já falhou **{entrada.get('tentativas')}** vezes ao registrar no servidor "
            f"e continua guardada na fila (nada foi perdido).\n"
            f"Último erro: `{entrada.get('ultimo_erro') or 'não informado'}`\n"
            f"Use `/aprovar_ficha` para forçar o registro manualmente."
        )

async def processar_fichas_pendentes(espera_estabilizacao=True):
    global fila_pendentes_em_espera, servidor_online
    if fila_pendentes_em_espera:
        return

    fila = carregar_fila_registro()
    if not fila:
        return

    if not aprovacao_automatica_ativa():
        print(f"[FICHAS] Aprovacao automatica DESLIGADA; {len(fila)} ficha(s) aguardando a staff.")
        return

    if not registros_estao_liberados():
        restantes = segundos_ate_abertura()
        print(f"[FICHAS] {len(fila)} ficha(s) guardada(s); aprovacao abre em {restantes // 60} min.")
        return

    fila_pendentes_em_espera = True
    try:
        if espera_estabilizacao:
            print(f"[FICHAS] {len(fila)} ficha(s) na fila; aguardando 5 minutos para o servidor estabilizar.")
            # Delay intencional para o servidor estabilizar antes de registrar em lote.
            await asyncio.sleep(300)

        if not servidor_online:
            print("[FICHAS] Servidor ainda offline; fila mantida intacta.")
            return

        resultado_rcon = await enviar_comando_rcon_detalhado("players")
        if not resultado_rcon.ok:
            servidor_online = False
            print(f"[FICHAS] RCON nao respondeu players; fila mantida intacta: {resultado_rcon.error}")
            return

        # Rede de seguranca: tickets com mais de uma ficha (enviadas antes da
        # trava existir) ficam so com a mais recente.
        manter_apenas_ficha_mais_recente()

        fila = carregar_fila_registro()
        if not fila:
            return

        liberadas = 0
        travadas = 0

        for p in fila:
            chave = (p.get("canal_id"), p.get("msg_id"))

            # Ja esta rodando: nao agenda de novo.
            if chave in fichas_em_processamento:
                continue

            try:
                canal = bot.get_channel(p.get("canal_id"))
                if not canal:
                    # Canal ainda nao carregou no cache: a entrada FICA na fila.
                    continue

                if p.get("tentativas", 0) >= MAX_TENTATIVAS_REGISTRO:
                    travadas += 1
                    await alertar_staff_ficha_travada(canal, p)
                    continue

                msg = await reconstruir_ficha_salva(canal, p)

                if p.get("estado") == ESTADO_AGUARDANDO_STAFF:
                    with suppress(Exception):
                        await canal.send("✅ **Sua ficha foi liberada!** Criando seu personagem agora...")
                elif p.get("estado") == ESTADO_AGUARDANDO_ABERTURA:
                    with suppress(Exception):
                        await canal.send("🎉 **Chegou a hora!** Os registros abriram — estou criando seu personagem agora...")
                elif p.get("estado") == ESTADO_AGUARDANDO_SERVIDOR:
                    with suppress(Exception):
                        await canal.send("🔄 **O servidor abriu!** Tirando sua ficha da fila de espera e registrando seu personagem agora...")

                atualizar_entrada_fila(p["canal_id"], p["msg_id"], estado=ESTADO_NA_FILA)

                if agendar_processamento_ficha(msg, bypass=False, checar_online=False):
                    liberadas += 1
            except Exception as erro:
                # A entrada PERMANECE na fila de proposito: sera tentada de novo.
                print(f"[FICHAS] Falha ao liberar ficha {p.get('msg_id')} (mantida na fila): {erro}")
                atualizar_entrada_fila(p["canal_id"], p["msg_id"], ultimo_erro=str(erro))

        restantes = len(carregar_fila_registro())
        print(f"[FICHAS] {liberadas} ficha(s) enviada(s) para registro; {restantes} ainda na fila; {travadas} aguardando a staff.")
    finally:
        fila_pendentes_em_espera = False

async def retomar_fichas_em_analise():
    """Roda no on_ready: reabre as fichas que estavam no meio da analise quando o
    bot caiu/reiniciou e continua a contagem de onde parou, sem perder nada."""
    analises = carregar_fichas_em_analise()
    if not analises:
        return

    # Roda antes da varredura geral de tickets (que espera 8s) para que o
    # controle de duplicidade em fichas_em_processamento ja esteja preenchido.
    await asyncio.sleep(4)

    restantes = []
    retomadas = 0

    for analise in analises:
        try:
            canal = bot.get_channel(analise.get("canal_id"))
            if not canal:
                restantes.append(analise)
                continue

            msg = await reconstruir_ficha_salva(canal, analise)

            try:
                fim = datetime.fromisoformat(analise.get("fim_analise"))
                segundos_restantes = max(0, int((fim - datetime.now()).total_seconds()))
            except Exception:
                segundos_restantes = ESPERA_ANALISE_FICHA_SEGUNDOS

            # Trava de sanidade: nunca esperar mais do que a analise completa.
            segundos_restantes = min(segundos_restantes, ESPERA_ANALISE_FICHA_SEGUNDOS)

            agendado = agendar_processamento_ficha(
                msg,
                bypass=analise.get("bypass", False),
                checar_online=analise.get("checar_online", True),
                segundos_espera=segundos_restantes,
                msg_espera_id=analise.get("msg_espera_id"),
            )
            if agendado:
                retomadas += 1
                print(f"[FICHAS] Retomando analise da ficha {msg.id} ({segundos_restantes}s restantes).")
        except discord.NotFound:
            print("[FICHAS] Ficha em analise nao existe mais (canal ou mensagem apagada); descartando.")
        except discord.Forbidden:
            print("[FICHAS] Sem permissao para retomar ficha em analise; descartando.")
        except Exception as erro:
            print(f"[FICHAS] Falha ao retomar ficha em analise: {erro}")
            restantes.append(analise)

    if len(restantes) != len(analises):
        salvar_fichas_em_analise(restantes)

    if retomadas:
        print(f"[FICHAS] {retomadas} ficha(s) retomada(s) apos reinicio.")

async def guardar_ficha_para_staff(message):
    """Ficha recebida com a aprovacao automatica desligada: fica guardada ate a
    staff aprovar manualmente."""
    ja_estava = ficha_ja_esta_pendente(carregar_fila_registro(), message.channel.id, message.id)
    registrar_na_fila(message, ESTADO_AGUARDANDO_STAFF)

    if ja_estava:
        return await message.channel.send(
            "⏳ **Sua ficha já está guardada** e aguardando a análise da staff. Não precisa mandar de novo."
        )

    await message.channel.send(
        "✅ **Ficha recebida!**\n\n"
        "No momento os personagens estão sendo **aprovados manualmente pela staff**, "
        "então o seu não é criado na hora.\n"
        "Sua ficha está **guardada em disco** — aguarde aqui neste ticket que a staff analisa e libera.\n"
        "*Você não precisa fazer mais nada nem reenviar a ficha.*"
    )

async def guardar_ficha_para_abertura(message):
    """Ficha enviada antes da hora marcada: fica guardada em disco ate abrir."""
    ja_estava = ficha_ja_esta_pendente(carregar_fila_registro(), message.channel.id, message.id)
    registrar_na_fila(message, ESTADO_AGUARDANDO_ABERTURA)

    if ja_estava:
        return await message.channel.send(
            f"⏳ **Sua ficha já está guardada.** {texto_abertura_discord()}\nNão precisa mandar de novo."
        )

    await message.channel.send(
        f"✅ **Ficha recebida e guardada!**\n\n{texto_abertura_discord()}\n"
        f"Seu personagem será criado automaticamente nesse horário — você **não precisa fazer mais nada** "
        f"e nem mandar a ficha de novo.\n"
        f"*A fila é gravada em disco: mesmo que o bot reinicie, sua ficha continua garantida.*"
    )

async def guardar_ficha_pendente(message):
    ja_estava = ficha_ja_esta_pendente(carregar_fila_registro(), message.channel.id, message.id)
    registrar_na_fila(message, ESTADO_AGUARDANDO_SERVIDOR)

    if ja_estava:
        await message.channel.send("⏳ **Sua ficha já está na fila de espera.** Assim que o servidor abrir, eu registro seu personagem automaticamente — não precisa mandar de novo.")
    else:
        await message.channel.send("⏳ **Servidor ainda não está online!** Sua ficha foi **salva na fila** e será registrada automaticamente assim que o servidor abrir.\n*(A fila é gravada em disco: mesmo que o bot reinicie, sua ficha continua garantida.)*")

async def buscar_formulario_ficha_aberto(canal, pendentes):
    async for mensagem in canal.history(limit=80):
        if mensagem_parece_formulario_ficha(mensagem):
            if ficha_ja_esta_pendente(pendentes, canal.id, mensagem.id):
                return None
            return mensagem

        if mensagem_bot_indica_ficha_processada(mensagem):
            return None

    return None

async def varrer_tickets_abertos_fichas():
    global varredura_fichas_executada
    if varredura_fichas_executada:
        return

    varredura_fichas_executada = True
    await asyncio.sleep(8)

    pendentes = carregar_fila_registro()
    total_encontradas = 0

    for guild in bot.guilds:
        for canal in guild.text_channels:
            if not categoria_processa_ficha_pos_morte(canal.category):
                continue

            try:
                formulario = await buscar_formulario_ficha_aberto(canal, pendentes)
                if not formulario:
                    continue

                # Nao registra ficha digitada: apenas avisa para refazer no botao.
                total_encontradas += 1
                await avisar_ficha_formato_antigo(canal, formulario.author)
                await asyncio.sleep(1)
            except discord.Forbidden:
                print(f"[FICHAS] Sem permissao para varrer o canal {canal.id}.")
            except Exception as erro:
                print(f"[FICHAS] Falha ao varrer o canal {canal.id}: {erro}")

    if total_encontradas:
        print(f"[FICHAS] Varredura inicial encontrou {total_encontradas} ficha(s) no formato antigo; jogadores avisados.")

async def agendar_remocao_vip(guild_id, user_id, cargo_id, canal_id, segundos_espera, chave_vip, vencimento_esperado):
    try:
        await asyncio.sleep(segundos_espera)

        vips = carregar_vips()
        if vips.get(chave_vip) != vencimento_esperado:
            return

        guild = bot.get_guild(guild_id)
        membro = guild.get_member(user_id) if guild else None
        cargo = guild.get_role(cargo_id) if guild else None
        if guild and membro and cargo:
            try:
                await membro.remove_roles(cargo, reason="VIP temporario expirado")
            except (discord.Forbidden, discord.HTTPException) as erro:
                # Mantem o registro e tenta novamente: apagar o registro aqui
                # faria o VIP ficar permanente caso a hierarquia esteja errada.
                print(f"[VIP] Falha ao remover o cargo expirado {chave_vip}: {erro}")
                agendar_remocao_vip_unica(
                    guild_id, user_id, cargo_id, canal_id, 300,
                    chave_vip, vencimento_esperado,
                )
                return

            mensagem_expiracao = (
                f"⚠ Olá! O seu tempo de VIP/Cargo **{cargo.name}** expirou no servidor "
                f"**{guild.name}**! Fale com a Staff para renovar."
            )
            try:
                await membro.send(mensagem_expiracao)
            except (discord.Forbidden, discord.HTTPException):
                print(f"[VIP] Nao consegui enviar PV de expiracao para {membro.id}.")

            # O aviso no canal e sempre enviado, mesmo quando o PV chegou,
            # para a staff ter um registro visivel do vencimento.
            canal = guild.get_channel(canal_id) if canal_id else None
            if canal:
                try:
                    await canal.send(
                        f"⚠ {membro.mention}, o VIP **{cargo.name}** expirou e o cargo foi removido. "
                        "Um aviso tambem foi enviado por PV."
                    )
                except (discord.Forbidden, discord.HTTPException) as erro:
                    print(f"[VIP] Nao consegui avisar expiracao no canal {canal_id}: {erro}")

        vips = carregar_vips()
        if vips.get(chave_vip) == vencimento_esperado:
            del vips[chave_vip]
            salvar_vips(vips)
    finally:
        if tarefas_remocao_vip.get(chave_vip) is asyncio.current_task():
            tarefas_remocao_vip.pop(chave_vip, None)

async def conceder_vip_temporario(guild, membro, cargo, quantidade, unidade, canal_id, motivo):
    """Concede/renova um VIP e deixa somente um vencimento por cargo e membro."""
    if quantidade < 1:
        raise ValueError("A quantidade precisa ser maior que zero.")

    await membro.add_roles(cargo, reason=motivo)
    if "minuto" in unidade.lower():
        segundos_totais = quantidade * 60
        vencimento = datetime.now() + timedelta(minutes=quantidade)
    else:
        segundos_totais = quantidade * 24 * 60 * 60
        vencimento = datetime.now() + timedelta(days=quantidade)
    vips = carregar_vips()
    prefixo_chave = f"{membro.id}_{cargo.id}_"

    # Uma renovacao substitui qualquer agendamento anterior do mesmo VIP,
    # mesmo que ele tenha sido concedido antes por outro canal ou pelo !zomboid.
    for chave_antiga in [chave for chave in vips if chave.startswith(prefixo_chave)]:
        tarefa_antiga = tarefas_remocao_vip.pop(chave_antiga, None)
        if tarefa_antiga and not tarefa_antiga.done():
            tarefa_antiga.cancel()
        del vips[chave_antiga]

    chave_vip = f"{membro.id}_{cargo.id}_{canal_id}"
    vencimento_iso = vencimento.isoformat()
    vips[chave_vip] = vencimento_iso
    salvar_vips(vips)
    agendar_remocao_vip_unica(
        guild.id, membro.id, cargo.id, canal_id,
        segundos_totais, chave_vip, vencimento_iso,
    )
    return vencimento

async def monitorar_mortes():
    if not CANAL_MORTES_ID: return
    caminhos = caminhos_mortes_friendhost()
    if not caminhos: return
    caminho_mortes = caminhos[0]

    print(f"📡 [VIGIA] Monitoramento de Mortes Ativado em {caminho_mortes}!")
    # Guarda as ultimas linhas ja anunciadas: se o mod reescrever o arquivo,
    # o bot nao repete a mesma morte no canal.
    mortes_anunciadas = deque(maxlen=200)

    with open(caminho_mortes, 'r', encoding='utf-8', errors='replace') as f:
        f.seek(0, 2)
        posicao = f.tell()

        while not bot.is_closed():
            try:
                # A FriendHost rotaciona/limpa os logs. Se o arquivo encolheu,
                # o tail antigo pararia de ver mortes para sempre em silencio.
                if detectar_rotacao_arquivo(caminho_mortes, posicao):
                    # O mod limita o historico reescrevendo o arquivo inteiro.
                    # Voltar ao inicio faria o bot reanunciar mortes antigas,
                    # entao continuamos do fim. A checagem do anti-fraude le o
                    # arquivo completo na hora do registro, nada se perde.
                    print("[VIGIA] Arquivo de mortes encolheu (rotacao/limite do mod); seguindo do fim.")
                    f.seek(0, 2)
                    posicao = f.tell()

                linha = f.readline()
                posicao = f.tell()

                if not linha:
                    await asyncio.sleep(1)
                    continue

                nomes_detectados = extrair_morte_da_linha(linha)
                if nomes_detectados is None:
                    continue

                assinatura = linha.strip()
                if assinatura in mortes_anunciadas:
                    continue

                nomes_mortos = filtrar_nomes_registrados(nomes_detectados) or nomes_detectados[:1]
                if not nomes_mortos:
                    print(f"[VIGIA] Linha de morte sem nome reconhecido: {assinatura[:200]}")
                    continue

                mortes_anunciadas.append(assinatura)

                # Marca todas as variacoes (login e nome do personagem) para o
                # anti-fraude achar depois, venha a ficha com qual dos dois vier.
                status_db = carregar_status()
                for nome in nomes_mortos:
                    status_db[normalizar_chave_personagem(nome)] = "morto"
                salvar_status(status_db)

                nome_exibido = nomes_mortos[-1]
                print(f"[VIGIA] Morte detectada: {', '.join(nomes_mortos)}")

                canal = bot.get_channel(int(CANAL_MORTES_ID))
                if canal:
                    embed = discord.Embed(title=" 💀 Jogador Morreu!", description=f"**{nome_exibido}** virou comida de zumbi.", color=0xef4444)
                    campos = campos_estruturados_morte(linha)
                    if len(campos) >= 3 and campos[1] and campos[2]:
                        embed.add_field(name="Horário", value=f"{campos[1]} - {campos[2]}")
                    else:
                        embed.add_field(name="Horário", value=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    await canal.send(embed=embed)
            except asyncio.CancelledError:
                raise
            except Exception as erro:
                # Falhar uma linha nunca pode derrubar o monitor inteiro.
                print(f"[VIGIA] Erro ao processar linha de morte (monitor continua ativo): {erro}")
                await asyncio.sleep(2)

async def monitorar_eventos():
    if not CANAL_EVENTOS_ID: return
    if not os.path.exists(CAMINHO_EVENTOS): return

    print("📡 [VIGIA] Monitoramento de Eventos Ativado!")
    with open(CAMINHO_EVENTOS, 'r', encoding='utf-8', errors='replace') as f:
        f.seek(0, 2)
        posicao = f.tell()

        while not bot.is_closed():
            try:
                if detectar_rotacao_arquivo(CAMINHO_EVENTOS, posicao):
                    print("[VIGIA] Log de eventos foi rotacionado; voltando para o inicio do arquivo.")
                    f.seek(0)
                    posicao = 0

                linha = f.readline()
                posicao = f.tell()

                if not linha:
                    await asyncio.sleep(1)
                    continue

                dados = linha.split(';')
                if len(dados) >= 4:
                    nome_evento = dados[3].replace('"', '').strip()
                    detalhes = " | ".join(dados)

                    canal = bot.get_channel(int(CANAL_EVENTOS_ID))
                    if canal:
                        embed = discord.Embed(title=" 🔔 Novo Evento no Servidor", description=f"**{nome_evento}** realizou uma ação.", color=0x6366f1)
                        embed.add_field(name="Detalhes", value=f"`{detalhes}`")
                        await canal.send(embed=embed)
            except asyncio.CancelledError:
                raise
            except Exception as erro:
                print(f"[VIGIA] Erro ao processar linha de evento (monitor continua ativo): {erro}")
                await asyncio.sleep(2)

async def monitorar_call_ingame():
    global controle_call_ingame
    await bot.wait_until_ready()
    print("🎧 [CALL IN-GAME] Monitoramento de call obrigatória ativado!")

    while not bot.is_closed():
        try:
            agora = time.monotonic()

            if not servidor_online:
                controle_call_ingame.clear()
                await asyncio.sleep(INTERVALO_MONITOR_CALL_INGAME)
                continue

            jogadores_online = await ler_jogadores_online_monitoramento()
            ids_em_call = ids_na_call_ingame()

            for user_id_str, dados in jogadores_online.items():
                personagem = dados.get("personagem")
                role_id = dados.get("role_id")
                role_name = dados.get("role_name") or ""
                registro = controle_call_ingame.get(user_id_str)
                esta_na_call = int(user_id_str) in ids_em_call

                isento, motivo_isencao = jogador_isento_call_ingame(user_id_str, dados)
                if isento:
                    if registro:
                        controle_call_ingame.pop(user_id_str, None)
                        print(f"[CALL IN-GAME] {personagem} isento ({motivo_isencao}); nao sera expulso.")
                    continue

                if esta_na_call:
                    if registro:
                        controle_call_ingame.pop(user_id_str, None)
                    continue

                if not registro:
                    controle_call_ingame[user_id_str] = {
                        "personagem": personagem,
                        "fora_call_desde": agora,
                        "ultimo_visto": agora,
                        "ultima_tentativa": 0.0,
                    }
                    print(f"[CALL IN-GAME] {personagem} ({role_name or 'user'}) está online fora da call {NOME_CALL_INGAME}. Aguardando {TEMPO_GRACA_CALL_INGAME}s antes de expulsar.")
                    continue

                registro["personagem"] = personagem
                registro["ultimo_visto"] = agora

                if agora - registro.get("fora_call_desde", agora) < TEMPO_GRACA_CALL_INGAME:
                    continue

                if agora - registro.get("ultima_tentativa", 0.0) < COOLDOWN_TENTATIVA_CALL_INGAME:
                    continue

                registro["ultima_tentativa"] = agora
                ok, detalhe = await expulsar_jogador_sem_call_ingame(
                    dados.get("username_jogo"), personagem
                )

                if ok:
                    registro["fora_call_desde"] = agora
                    print(f"[CALL IN-GAME] {personagem} foi expulso por nao estar na call {NOME_CALL_INGAME}. Detalhe: {detalhe}")
                    await avisar_jogador_expulso_call(user_id_str, personagem)
                else:
                    print(f"[CALL IN-GAME] Falha ao expulsar {personagem}: {detalhe}")

            for user_id_str in list(controle_call_ingame.keys()):
                registro = controle_call_ingame.get(user_id_str)
                if not registro:
                    continue
                if user_id_str in jogadores_online:
                    continue
                if agora - registro.get("ultimo_visto", 0.0) >= TOLERANCIA_SUMICO_CALL_INGAME:
                    controle_call_ingame.pop(user_id_str, None)

        except Exception as erro:
            print(f"[CALL IN-GAME] Erro no monitor: {erro}")

        await asyncio.sleep(INTERVALO_MONITOR_CALL_INGAME)

async def processar_registro_pos_morte(message: discord.Message, bypass=False, checar_online=True, segundos_espera=None, msg_espera_id=None):
    global servidor_online
    # Enquanto for True, a ficha PERMANECE na fila duravel para ser tentada de
    # novo. So vira False quando o desfecho e definitivo (registrado com sucesso
    # ou recusado por regra). O padrao e "nao perder": qualquer caminho novo que
    # eu esqueca de marcar mantem a ficha guardada.
    manter_na_fila = True
    try:
        # A leitura e a validacao de formato vem ANTES de qualquer espera. Assim,
        # com o servidor fechado ou a abertura agendada, o jogador ja descobre na
        # hora se errou o nome ou a senha, em vez de so no dia seguinte.
        nome_novo_raw, senha_raw = extrair_dados_ficha(message.content)
        profissao_raw = extrair_profissao_ficha(message.content)
        historia_raw = extrair_historia_ficha(message.content)

        if not nome_novo_raw and not senha_raw:
            manter_na_fila = False
            return
        if not nome_novo_raw or not senha_raw:
            manter_na_fila = False
            return await message.channel.send("❌ **Erro na Análise:** Encontrei parte da ficha, mas faltou o **Nome** ou a **Senha**. Envie os dois dados no ticket.")

        nome_novo_raw = re.sub(r'[*`_~\u200b]', '', nome_novo_raw).strip()
        senha_raw = re.sub(r'[*`_~\u200b]', '', senha_raw).strip()
        nome_novo_limpo = remover_acentos(nome_novo_raw)

        if not re.match(r'^[a-zA-Z0-9_ ]+$', nome_novo_limpo):
            manter_na_fila = False
            return await message.channel.send("❌ **REGISTRO CANCELADO:** O nome não pode conter caracteres especiais (aspas, símbolos, etc). Mande a ficha novamente.")

        if not senha_ficha_valida(senha_raw):
            manter_na_fila = False
            return await message.channel.send("❌ **REGISTRO CANCELADO:** A senha não pode ter símbolos, espaços ou acentos. Use apenas letras e números. Mande a ficha novamente.")

        # Uma ficha por ticket. Ignora a propria entrada para nao se auto-barrar
        # quando a fila e reprocessada.
        if not bypass and ficha_ativa_no_canal(message.channel.id, ignorar_msg_id=message.id):
            manter_na_fila = False
            return await message.channel.send(
                "🚫 **Já existe uma ficha em andamento neste ticket.**\n"
                "Só vale **uma ficha por ticket** — a que você enviou antes continua valendo.\n"
                "Se errou algum dado, use o botão **🗑 Fechar Ticket** e abra um novo. Isso **não gasta vida**."
            )

        # Portao 1: aprovacao automatica desligada -> so a staff libera.
        if not bypass and not aprovacao_automatica_ativa():
            await guardar_ficha_para_staff(message)
            return

        # Portao 2: agendamento. A ficha entra na fila duravel e espera a hora
        # marcada. Nada e perdido nem aprovado antes do tempo.
        if not bypass and not registros_estao_liberados():
            await guardar_ficha_para_abertura(message)
            return

        if checar_online:
            if not servidor_online:
                await guardar_ficha_pendente(message)
                return

            resultado_online = await enviar_comando_rcon_detalhado("players")
            if not resultado_online.ok:
                servidor_online = False
                await guardar_ficha_pendente(message)
                return

        db_personagens = carregar_personagens()
        user_id_str = str(message.author.id)
        personagem_antigo = db_personagens.get(user_id_str)
        status_db = carregar_status()

        primeiro_registro = False
        aprovado_manual = False
        aprovado_mod = False
        msg_espera = None

        # Limite de vidas: checado ANTES dos 3 minutos de analise, para o jogador
        # nao ficar esperando so para ouvir que nao pode criar. O bypass da staff
        # (/aprovar_ficha) ignora o limite de proposito.
        if not bypass:
            pode_criar, vidas_jogador = jogador_pode_criar_personagem(user_id_str, bool(personagem_antigo))
            if not pode_criar:
                manter_na_fila = False
                return await message.channel.send(
                    f"💀 **VIDAS ESGOTADAS:** {message.author.mention}, você já usou todas as suas "
                    f"**{vidas_jogador['total']}** vidas desta temporada e não pode criar outro personagem.\n"
                    f"*(Staff: use `/adicionar_vidas` para liberar uma vida extra, ou `/aprovar_ficha` para ignorar o limite)*"
                )

        if not bypass:
            espera_restante = ESPERA_ANALISE_FICHA_SEGUNDOS if segundos_espera is None else max(0, int(segundos_espera))

            if msg_espera_id:
                with suppress(Exception):
                    msg_espera = await message.channel.fetch_message(msg_espera_id)

            if not msg_espera:
                minutos = max(1, round(espera_restante / 60))
                msg_espera = await message.channel.send(f"⏳ **Estamos analisando seu personagem.** Aguarde **{minutos} minuto(s)** enquanto confirmo os dados e consulto o histórico do servidor.")

            registrar_ficha_em_analise(
                message,
                msg_espera.id if msg_espera else None,
                datetime.now() + timedelta(seconds=espera_restante),
                bypass=bypass,
                checar_online=checar_online,
            )

            if espera_restante > 0:
                await asyncio.sleep(espera_restante)

            nome_bloqueado = encontrar_nome_bloqueado_por_historico(user_id_str, nome_novo_limpo, db_personagens)
            if nome_bloqueado:
                manter_na_fila = False
                if msg_espera:
                    try: await msg_espera.delete()
                    except Exception: pass
                return await message.channel.send(f"🛑 **Nome bloqueado:** o nome **{nome_novo_limpo}** corresponde a um personagem anterior seu (`{nome_bloqueado}`). Escolha um nome e sobrenome totalmente novos para o próximo personagem.")

            if not personagem_antigo:
                primeiro_registro = True
                aprovado_manual = True 
            else:
                chave_antiga = normalizar_chave_personagem(personagem_antigo)

                status_antigo = str(status_db.get(chave_antiga, "")).lower().strip()
                if status_antigo == "morto":
                    aprovado_manual = True

                if not aprovado_manual and personagem_esta_morto(personagem_antigo):
                    aprovado_mod = True

                if not aprovado_manual and not aprovado_mod:
                    manter_na_fila = False
                    if msg_espera:
                        try: await msg_espera.delete()
                        except Exception: pass
                    return await message.channel.send(f"🛑 **SISTEMA ANTI-FRAUDE:** O seu personagem atual (`{personagem_antigo}`) ainda NÃO consta como morto no banco de dados do jogo. Registro bloqueado.\n*(Staff: Use `/aprovar_ficha` para ignorar)*")

                if aprovado_manual:
                    del status_db[chave_antiga]
                    salvar_status(status_db)

        if msg_espera:
            try: await msg_espera.delete()
            except: pass

        if not senha_ficha_valida(senha_raw):
            manter_na_fila = False
            if not bypass and not primeiro_registro and aprovado_manual:
                status_db[chave_antiga] = "morto"
                salvar_status(status_db)
            return await message.channel.send("❌ **REGISTRO CANCELADO:** A senha não pode ter símbolos, espaços ou acentos. Mande a ficha novamente.")

        def devolver_status_antigo():
            """Recoloca o personagem antigo como 'morto' para a ficha continuar
            aprovada na proxima tentativa."""
            if not bypass and not primeiro_registro and aprovado_manual:
                status_db[chave_antiga] = "morto"
                salvar_status(status_db)

        # Marca em disco ANTES de falar com o servidor. Se o bot cair no meio do
        # adduser, a proxima tentativa sabe que o comando ja pode ter chegado la.
        entrada_fila = registrar_na_fila(message, ESTADO_REGISTRANDO)
        rcon_ja_tentado = bool(entrada_fila.get("rcon_enviado"))
        tentativas = int(entrada_fila.get("tentativas") or 0) + 1

        await message.channel.send("⚡ Ficha aprovada! Conectando ao RCON do Project Zomboid...")
        atualizar_entrada_fila(message.channel.id, message.id, rcon_enviado=True, tentativas=tentativas)

        # O semaforo protege so o RCON, que e o recurso escasso de verdade.
        async with semaforo_rcon_registro:
            resposta_rcon = await enviar_comando_rcon(f'adduser "{nome_novo_limpo}" "{senha_raw}"')

        if "Erro RCON:" in resposta_rcon:
            # Falha de CONEXAO: a ficha volta para a fila e sera tentada de novo
            # automaticamente. Nada e descartado.
            servidor_online = False
            devolver_status_antigo()
            atualizar_entrada_fila(message.channel.id, message.id, estado=ESTADO_AGUARDANDO_SERVIDOR, ultimo_erro=resposta_rcon)
            return await message.channel.send(
                f"⏳ **O servidor não respondeu agora.** Sua ficha **continua salva na fila** (tentativa {tentativas}) "
                f"e será registrada automaticamente assim que o servidor responder. Você não precisa mandar de novo.\n"
                f"*Detalhe técnico: `{resposta_rcon}`*"
            )

        texto_rcon = (resposta_rcon or "").lower()
        nome_ja_existe = "already exist" in texto_rcon or "user already" in texto_rcon or "username already" in texto_rcon

        if resposta_rcon_indica_falha_cadastro(resposta_rcon):
            if nome_ja_existe and rcon_ja_tentado:
                # Ja tinhamos enviado o adduser antes (o bot caiu logo depois).
                # O login existe porque FOMOS NOS que criamos: isso e sucesso.
                print(f"[FICHAS] '{nome_novo_limpo}' ja existia de uma tentativa anterior desta mesma ficha; tratando como sucesso.")
            elif nome_ja_existe:
                manter_na_fila = False
                devolver_status_antigo()
                return await message.channel.send(f"❌ **NOME JÁ EM USO:** já existe um login **{nome_novo_limpo}** no servidor. Escolha outro nome e mande a ficha novamente.")
            else:
                devolver_status_antigo()
                atualizar_entrada_fila(message.channel.id, message.id, estado=ESTADO_AGUARDANDO_SERVIDOR, ultimo_erro=resposta_rcon)
                return await message.channel.send(
                    f"⏳ **O servidor não confirmou a criação do login.** Sua ficha **continua salva na fila** (tentativa {tentativas}) "
                    f"e vou tentar de novo automaticamente.\n*Detalhe técnico: `{resposta_rcon or 'resposta vazia do servidor'}`*"
                )

        if personagem_antigo:
            registrar_personagem_no_historico(user_id_str, personagem_antigo)
        registrar_personagem_no_historico(user_id_str, nome_novo_limpo)
        salvar_ultimo_registro_personagem(message, nome_novo_limpo, senha_raw, historia_raw, profissao_raw)
        db_personagens[user_id_str] = nome_novo_limpo
        salvar_personagens(db_personagens)

        # SO AQUI o registro esta 100% confirmado: usuario criado no jogo e
        # gravado em disco. Agora sim a ficha pode sair da fila duravel.
        manter_na_fila = False
        remover_da_fila_registro(message.channel.id, message.id)
        remover_ficha_em_analise(message.channel.id, message.id)
        print(f"[FICHAS] Registro confirmado: {nome_novo_limpo} (discord {user_id_str}).")

        # Vida so e consumida em RECRIACAO: o primeiro personagem da temporada
        # e gratuito. E so depois do registro estar confirmado no servidor.
        houve_personagem_anterior = bool(personagem_antigo)
        if houve_personagem_anterior:
            vidas_atuais = consumir_vida(user_id_str)
        else:
            vidas_atuais = calcular_vidas(user_id_str)

        with suppress(Exception):
            await registrar_log_vidas(
                message.author, nome_novo_limpo,
                vidas_atuais, primeiro_personagem=not houve_personagem_anterior,
            )

        aviso_nick = ""
        try:
            await message.author.edit(nick=nome_novo_limpo[:32])
            aviso_nick = f"Seu apelido no servidor foi alterado para **{nome_novo_limpo[:32]}**."
        except discord.Forbidden:
            aviso_nick = "*(O bot não tem permissão para mudar seu apelido automaticamente)*."
        except discord.HTTPException:
            aviso_nick = "*(Não consegui alterar seu apelido no Discord, mas o registro no jogo foi concluído.)*"

        embed = discord.Embed(title="✅ Registro Concluído com Sucesso!", color=discord.Color.green())
        embed.add_field(name="Login", value=f"```{nome_novo_limpo}```", inline=False)
        embed.add_field(name="Vidas", value=texto_vidas_restantes(vidas_atuais), inline=False)
        minutos_ticket = minutos_fechar_ticket()
        aviso_fechamento = (
            f"Este ticket se fecha sozinho em **{minutos_ticket} minuto(s)**."
            if minutos_ticket else
            "Quando terminar de anotar seus dados, use o botão **🗑 Fechar Ticket**."
        )
        embed.description = f"{aviso_nick}\n\n**Seus dados de acesso foram enviados no seu PV (DM)!**\n{aviso_fechamento}"

        try:
            dm_embed = discord.Embed(title="🔑 Seus dados de acesso", color=discord.Color.green())
            dm_embed.add_field(name="Login", value=f"```{nome_novo_limpo}```", inline=False)
            dm_embed.add_field(name="Senha", value=f"```{senha_raw}```", inline=False)
            dm_embed.set_footer(text="Guarde esses dados com segurança!")
            await message.author.send(embed=dm_embed)
        except discord.Forbidden:
            embed.add_field(name="Senha", value=f"```{senha_raw}```", inline=False)
            embed.description = f"{aviso_nick}\n\n**Copie e salve seus dados!** (DM bloqueada, enviando aqui)\n{aviso_fechamento}"

        await message.channel.send(content=message.author.mention, embed=embed)

        if minutos_ticket:
            agendar_fechamento_ticket(message.channel.id, minutos_ticket)

    except Exception as e:
        # Erro inesperado conta como transitorio: a ficha fica na fila e sera
        # tentada de novo. O limite de tentativas evita loop infinito.
        print(f"[FICHAS] Erro interno ao processar ficha {message.id}: {e}")
        with suppress(Exception):
            atualizar_entrada_fila(message.channel.id, message.id, estado=ESTADO_AGUARDANDO_SERVIDOR, ultimo_erro=str(e))
        with suppress(Exception):
            await message.channel.send("⚠ **Tive um problema interno ao processar sua ficha.** Ela **continua salva na fila** e vou tentar de novo automaticamente.")
    finally:
        # Rede de seguranca: a analise em disco sempre e limpa...
        with suppress(Exception):
            remover_ficha_em_analise(message.channel.id, message.id)
        # ...mas a fila duravel so e limpa quando o desfecho foi definitivo.
        if not manter_na_fila:
            with suppress(Exception):
                remover_da_fila_registro(message.channel.id, message.id)

CONTEXTO_ROTEADOR = """
Você é a inteligência artificial central do ZomboidOS, assistente do servidor Organic RP.
Você tem DUAS funções:
1. Bate-papo: Se o usuário perguntar algo, responda NATURALMENTE. Não crie canais a menos que peçam diretamente "crie o canal X".
REGRAS DE OURO: Se o usuário pedir para "trazer de volta", "recuperar" ou "restaurar" um cargo ou canal apagado, NÃO use o comando de deletar. Use o comando de CRIAR (CMD:CRIAR_CARGO ou CMD:CRIAR_CANAL) e avise no bate-papo de forma natural que o Discord não permite restaurar arquivos apagados, então você recriou um NOVO com o mesmo nome.
Se o usuário pedir para SUGERIR um emoji, nome ou texto, NÃO gere CMD. Responda naturalmente com sugestões curtas.
Se o usuário perguntar se você entendeu, responda naturalmente explicando o que entendeu. NÃO gere CMD.
NUNCA invente comandos fora da lista abaixo. Se a ação não existir, responda naturalmente explicando a limitação.

2. Comandos de Ação: SE o usuário pedir para realizar uma ação, responda EXCLUSIVAMENTE com UMA LINHA contendo o código CMD.
Se a ação envolver mensagem com múltiplas linhas, escreva as quebras como \n dentro do próprio CMD.

Ações CMD:
- Entrar na voz: CMD:ENTRAR_VOZ
- Gravar: CMD:GRAVAR_VOZ
- Parar: CMD:PARAR_VOZ
- Criar cargo: CMD:CRIAR_CARGO|NomeDoCargo|Cor
- Apagar/Excluir cargo do servidor: CMD:DELETAR_CARGO|NomeDoCargo
- Tirar/Remover cargo de um jogador: CMD:REMOVER_CARGO|NomeDoCargo|ID_do_User
- Criar Canal: CMD:CRIAR_CANAL|NomeDoCanal|Privado(sim/nao)
- Dar cargo PERMANENTE: CMD:ADD_ROLE|NomeDoCargo|ID_do_User
- Dar cargo/VIP TEMPORRIO: CMD:DAR_VIP|NomeDoVIP|ID_do_User|Quantidade|Unidade
- Remover/Apagar VIP de um jogador antes do tempo: CMD:REMOVER_REGISTRO_VIP|ID_do_User
- Adicionar ou Diminuir tempo de um VIP já existente: CMD:MODIFICAR_VIP|Ação(adicionar/diminuir)|ID_do_User|Quantidade|Unidade
- Limpar todo o registro de VIPs (zerar todos os VIPs do banco de dados): CMD:LIMPAR_TODOS_VIPS
- Enviar uma mensagem em um canal: CMD:ENVIAR_MENSAGEM_CANAL|CanalOuID|Mensagem com \n para quebra de linha
- Editar uma mensagem já enviada em um canal: CMD:EDITAR_MENSAGEM_CANAL|CanalOuID|MensagemID|Novo texto com \n
- Apagar uma mensagem de um canal: CMD:APAGAR_MENSAGEM_CANAL|CanalOuID|MensagemID
- Renomear um canal: CMD:RENOMEAR_CANAL|CanalOuID|NovoNome
- Mover um canal para uma categoria: CMD:MOVER_CANAL|CanalOuID|NomeDaCategoria
- Salvar um template de mensagem: CMD:SALVAR_TEMPLATE|NomeTemplate|Mensagem com \n
- Enviar um template salvo em um canal: CMD:ENVIAR_TEMPLATE|CanalOuID|NomeTemplate
- Adicionar/trocar emoji que representa um canal no nome dele: CMD:EMOJI_CANAL|CanalOuID|Emoji
- Consultar o último registro de personagem de um jogador: CMD:CONSULTAR_REGISTRO_PERSONAGEM|IDOuNomeDoPlayer
- Fechar canais/tickets: CMD:FECHAR_CANAIS|canal1,canal2
- Fechar TODOS tickets de categoria: CMD:FECHAR_CATEGORIA|NomeDaCategoria
"""
CONTEXTO_ATA_GEMINI = """
Você é um analista de reuniões em português do Brasil.
Sua tarefa é ouvir o áudio de uma call e produzir uma ata útil, clara e objetiva.

Regras:
- Resuma o que realmente foi discutido.
- Ignore brincadeiras, trechos repetitivos e conversas paralelas sem relevância.
- Não invente falas, decisões ou responsáveis.
- Se algo estiver ambíguo ou inaudível, deixe isso explícito.
- Seja direto, mas sem resumir demais.

Formato desejado:
**Resumo Executivo**
1 parágrafo com o tema central e o resultado da reunião.

**Pontos Discutidos**
- itens curtos e objetivos

**Decisões e Definições**
- itens curtos; se não houver decisão, diga isso

**Pendências e Próximos Passos**
- itens curtos; se não houver responsável claro, escreva "responsável não identificado"
""".strip()

BYTES_POR_SEGUNDO_PCM = 48000 * 1 * 2
MINIMO_BYTES_REUNIAO = BYTES_POR_SEGUNDO_PCM * 5
MAX_BYTES_REUNIAO = BYTES_POR_SEGUNDO_PCM * MAX_DURACAO_REUNIAO_SEGUNDOS

def converter_pcm_estereo_para_mono(pcm):
    tamanho_alinhado = len(pcm) - (len(pcm) % 4)
    amostras = array("h")
    amostras.frombytes(pcm[:tamanho_alinhado])
    return amostras[::2].tobytes()

@dataclass
class ReuniaoSession:
    guild_id: int
    canal_voz_id: int
    canal_texto_id: int
    iniciado_por_id: int
    iniciado_em: datetime
    arquivo_wav: str
    sink: "ReuniaoRecorderSink"
    participantes_iniciais: dict

class ReuniaoRecorderSink(voice_recv.AudioSink):
    CHANNELS = 1
    SAMPLE_WIDTH = 2
    SAMPLE_RATE = 48000

    def __init__(self, arquivo_destino):
        super().__init__()
        self.arquivo_destino = arquivo_destino
        self._arquivo = wave.open(arquivo_destino, 'wb')
        self._arquivo.setnchannels(self.CHANNELS)
        self._arquivo.setsampwidth(self.SAMPLE_WIDTH)
        self._arquivo.setframerate(self.SAMPLE_RATE)
        self.total_bytes = 0
        self.falas = {}
        self._fechado = False
        self.limite_atingido = False

    def wants_opus(self):
        return False

    def write(self, user, data):
        if self._fechado or self.limite_atingido:
            return

        pcm = getattr(data, "pcm", None)
        if not pcm:
            return

        pcm = converter_pcm_estereo_para_mono(pcm)
        restantes = MAX_BYTES_REUNIAO - self.total_bytes
        if restantes <= 0:
            self.limite_atingido = True
            return
        if len(pcm) > restantes:
            pcm = pcm[:restantes - (restantes % self.SAMPLE_WIDTH)]
            self.limite_atingido = True

        self._arquivo.writeframes(pcm)
        self.total_bytes += len(pcm)

        if not user or getattr(user, "bot", False):
            return

        nome = getattr(user, "display_name", None) or getattr(user, "name", None) or str(user)
        info = self.falas.setdefault(user.id, {"nome": nome, "bytes": 0})
        info["nome"] = nome
        info["bytes"] += len(pcm)

    def cleanup(self):
        if self._fechado:
            return
        self._fechado = True
        try:
            self._arquivo.close()
        except Exception:
            pass

    def duracao_segundos(self):
        return self.total_bytes / BYTES_POR_SEGUNDO_PCM if self.total_bytes else 0.0

    def principais_falantes(self):
        falantes = []
        for info in sorted(self.falas.values(), key=lambda item: item["bytes"], reverse=True):
            falantes.append({
                "nome": info["nome"],
                "segundos": info["bytes"] / BYTES_POR_SEGUNDO_PCM if info["bytes"] else 0.0,
            })
        return falantes

def gerar_caminho_audio_reuniao(guild_id):
    base_nome = os.path.splitext(os.path.basename(ARQUIVO_AUDIO))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(BASE_DIR, f"{base_nome}_{guild_id}_{timestamp}.wav")

def formatar_duracao_audio(segundos):
    segundos = max(0, int(round(segundos or 0)))
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    if horas:
        return f"{horas}h {minutos:02d}m {segundos:02d}s"
    if minutos:
        return f"{minutos}m {segundos:02d}s"
    return f"{segundos}s"

def dividir_texto_discord(texto, limite=1900):
    texto = (texto or "").strip()
    if not texto:
        return []
    if len(texto) <= limite:
        return [texto]

    partes = []
    atual = ""
    for bloco in texto.split("\n\n"):
        bloco = bloco.strip()
        if not bloco:
            continue
        candidato = bloco if not atual else f"{atual}\n\n{bloco}"
        if len(candidato) <= limite:
            atual = candidato
            continue

        if atual:
            partes.append(atual)
            atual = ""

        while len(bloco) > limite:
            corte = bloco.rfind("\n", 0, limite)
            if corte <= 0:
                corte = limite
            partes.append(bloco[:corte].strip())
            bloco = bloco[corte:].strip()
        atual = bloco

    if atual:
        partes.append(atual)

    return partes

def coletar_participantes_reuniao(sessao, canal_voz=None):
    participantes = dict(sessao.participantes_iniciais)

    if canal_voz:
        for membro in canal_voz.members:
            if not membro.bot:
                participantes[membro.id] = membro.display_name

    for user_id, info in sessao.sink.falas.items():
        participantes[user_id] = info["nome"]

    return sorted({nome.strip() for nome in participantes.values() if nome and nome.strip()}, key=normalizar_chave_personagem)

def formatar_principais_falantes(sessao):
    falantes = sessao.sink.principais_falantes()
    if not falantes:
        return "Nenhum falante identificado com clareza."
    return ", ".join(
        f"{info['nome']} (~{formatar_duracao_audio(info['segundos'])})"
        for info in falantes[:8]
    )

async def publicar_relatorio_reuniao(canal_texto, msg_status, texto):
    partes = dividir_texto_discord(texto)
    if not partes:
        partes = ["❌ **Erro:** não consegui gerar texto para a ata."]

    await msg_status.edit(content=partes[0])
    for parte in partes[1:]:
        await canal_texto.send(parte)

async def conectar_bot_na_call_do_autor(autor):
    canal_voz = getattr(getattr(autor, "voice", None), "channel", None)
    if not canal_voz:
        return None, "❌ Você precisa estar em uma call para eu entrar e gravar a reunião."

    guild = autor.guild
    vc = guild.voice_client

    if vc and vc.is_connected() and not hasattr(vc, "listen"):
        with suppress(Exception):
            await vc.disconnect()
        vc = None

    if vc and vc.is_connected() and getattr(vc, "channel", None) and vc.channel.id != canal_voz.id:
        if getattr(vc, "is_listening", lambda: False)():
            return None, "❌ Já existe uma gravação em andamento em outra call. Pare a reunião atual antes de me mover."
        await vc.move_to(canal_voz)
        return vc, None

    if vc and vc.is_connected():
        return vc, None

    vc = await canal_voz.connect(cls=voice_recv.VoiceRecvClient)
    return vc, None

async def iniciar_gravacao_reuniao(autor, canal_texto):
    guild = autor.guild
    sessao_atual = gravadores.get(guild.id)
    vc = guild.voice_client

    if sessao_atual and vc and vc.is_connected() and getattr(vc, "is_listening", lambda: False)():
        return False, "❌ Já existe uma gravação de reunião em andamento neste servidor."

    vc, erro = await conectar_bot_na_call_do_autor(autor)
    if erro:
        return False, erro

    if not vc or not vc.is_connected():
        return False, "❌ Não consegui conectar na call para iniciar a reunião."

    if getattr(vc, "is_listening", lambda: False)():
        return False, "❌ Eu já estou gravando esta call."

    arquivo_wav = gerar_caminho_audio_reuniao(guild.id)
    sink = ReuniaoRecorderSink(arquivo_wav)
    participantes_iniciais = {
        membro.id: membro.display_name
        for membro in vc.channel.members
        if not membro.bot
    }

    try:
        vc.listen(sink)
    except Exception as erro_listen:
        sink.cleanup()
        with suppress(Exception):
            os.remove(arquivo_wav)
        return False, f"❌ Não consegui iniciar a gravação da reunião: {erro_listen}"

    gravadores[guild.id] = ReuniaoSession(
        guild_id=guild.id,
        canal_voz_id=vc.channel.id,
        canal_texto_id=canal_texto.id,
        iniciado_por_id=autor.id,
        iniciado_em=datetime.now(),
        arquivo_wav=arquivo_wav,
        sink=sink,
        participantes_iniciais=participantes_iniciais,
    )

    return True, f"🔴 **Gravação iniciada.** Vou registrar a reunião em **{vc.channel.mention}** e gerar uma ata resumida quando você mandar parar."

# =========================================================
# V149: CAMADA RCON BLINDADA (SESSAO, RECONEXAO E LOCK)
# =========================================================
async def enviar_comando_rcon_detalhado(comando):
    return await rcon_manager.execute(comando)

async def enviar_comando_rcon(comando):
    resultado = await enviar_comando_rcon_detalhado(comando)
    if resultado.ok:
        return resultado.output

    detalhe_tentativas = f" apos {resultado.attempts} tentativa(s)" if resultado.attempts else ""
    return f"Erro RCON: {resultado.error}{detalhe_tentativas}"

async def processar_audio_gemini(arquivo_wav, contexto_reuniao):
    audio_file = None
    try:
        chave_da_vez = next(roleta_gemini)
        genai.configure(api_key=chave_da_vez)
        audio_file = await asyncio.wait_for(
            asyncio.to_thread(genai.upload_file, arquivo_wav),
            timeout=120.0,
        )
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"{CONTEXTO_ATA_GEMINI}\n\nContexto adicional da reunião:\n{contexto_reuniao}"
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, [prompt, audio_file]),
            timeout=240.0,
        )
        texto = getattr(response, "text", "") or ""
        return texto.strip() or "Não consegui extrair uma ata textual útil deste áudio."
    except Exception as e:
        return f"Erro Gemini: {e}"
    finally:
        if audio_file is not None:
            with suppress(Exception):
                await asyncio.to_thread(audio_file.delete)

async def encerrar_gravacao_reuniao(guild, canal_texto):
    sessao = gravadores.get(guild.id)
    vc = guild.voice_client

    if not sessao:
        if vc and vc.is_connected() and not getattr(vc, "is_listening", lambda: False)():
            with suppress(Exception):
                await vc.disconnect()
        return False, "❌ Não há nenhuma reunião sendo gravada neste servidor."

    canal_voz = getattr(vc, "channel", None) if vc else None
    participantes = coletar_participantes_reuniao(sessao, canal_voz)
    nomes_participantes = ", ".join(participantes) if participantes else "Não consegui identificar os participantes."
    principais_falantes = formatar_principais_falantes(sessao)
    duracao = sessao.sink.duracao_segundos()

    msg_status = await canal_texto.send("⚡ **Encerrando a gravação e preparando a ata da reunião...**")

    try:
        if vc and vc.is_connected() and getattr(vc, "is_listening", lambda: False)():
            vc.stop_listening()
            await asyncio.sleep(1.0)

        sessao.sink.cleanup()

        if vc and vc.is_connected():
            with suppress(Exception):
                await vc.disconnect()

        if sessao.sink.total_bytes < MINIMO_BYTES_REUNIAO or duracao < 5:
            await msg_status.edit(content="❌ **Erro:** o áudio ficou curto ou vazio demais para gerar uma ata confiável.")
            return True, "audio_curto"

        nome_canal = canal_voz.name if canal_voz else "Call desconhecida"
        contexto_reuniao = (
            f"Canal de voz: {nome_canal}\n"
            f"Início: {sessao.iniciado_em.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"Duração estimada do áudio: {formatar_duracao_audio(duracao)}\n"
            f"Participantes identificados: {nomes_participantes}\n"
            f"Principais falantes por tempo detectado: {principais_falantes}\n"
            "Ignore conversas paralelas bobas e priorize decisões, alinhamentos, problemas citados e próximos passos."
        )

        resumo = await processar_audio_gemini(sessao.arquivo_wav, contexto_reuniao)
        aviso_limite = "\n\n⚠ A gravação atingiu o limite configurado e a ata considera apenas a parte inicial da reunião." if sessao.sink.limite_atingido else ""

        cabecalho = (
            f"**📋 Ata da Reunião**\n"
            f"**Canal:** `{nome_canal}`\n"
            f"**Início:** `{sessao.iniciado_em.strftime('%d/%m/%Y %H:%M:%S')}`\n"
            f"**Duração capturada:** `{formatar_duracao_audio(duracao)}`\n"
            f"**Participantes:** {nomes_participantes}\n"
            f"**Principais falantes:** {principais_falantes}\n\n"
            f"{resumo}{aviso_limite}"
        )
        await publicar_relatorio_reuniao(canal_texto, msg_status, cabecalho)
        return True, "ok"
    finally:
        gravadores.pop(guild.id, None)
        with suppress(Exception):
            sessao.sink.cleanup()
        with suppress(Exception):
            if os.path.exists(sessao.arquivo_wav):
                os.remove(sessao.arquivo_wav)

async def roteador_groq(chat_id, user_msg):
    try:
        agora = time.monotonic()
        expiradas = [
            chave for chave, ultimo_uso in memorias_ultima_atividade.items()
            if agora - ultimo_uso >= MEMORIA_IA_TTL
        ]
        for chave in expiradas:
            memorias.pop(chave, None)
            memorias_ultima_atividade.pop(chave, None)

        excesso = len(memorias) - MAX_CANAIS_MEMORIA_IA + 1
        if excesso > 0 and chat_id not in memorias:
            chaves_antigas = sorted(memorias, key=lambda chave: memorias_ultima_atividade.get(chave, 0))[:excesso]
            for chave in chaves_antigas:
                memorias.pop(chave, None)
                memorias_ultima_atividade.pop(chave, None)

        historico = memorias.setdefault(chat_id, [{"role": "system", "content": CONTEXTO_ROTEADOR}])
        historico.append({"role": "user", "content": user_msg})
        if len(historico) > MAX_MENSAGENS_MEMORIA_IA:
            del historico[1:len(historico) - MAX_MENSAGENS_MEMORIA_IA + 1]
        memorias_ultima_atividade[chat_id] = agora

        completion = await asyncio.wait_for(
            asyncio.to_thread(client_groq.chat.completions.create, model="llama-3.3-70b-versatile", messages=historico, temperature=0.3),
            timeout=15.0
        )
        return completion.choices[0].message.content
    except asyncio.TimeoutError:
        return "Erro: O servidor da IA demorou muito para responder."
    except Exception as e:
        return f"Erro Groq: {e}"

def pegar_cor(nome_cor):
    if not nome_cor: return discord.Color.default()
    c = nome_cor.lower().strip()
    mapa = {
        'blue': discord.Color.blue(), 'azul': discord.Color.blue(),
        'red': discord.Color.red(), 'vermelho': discord.Color.red(),
        'green': discord.Color.green(), 'verde': discord.Color.green(),
        'gold': discord.Color.gold(), 'amarelo': discord.Color.gold(), 'ouro': discord.Color.gold(),
        'pink': discord.Color.from_rgb(255, 105, 180), 'rosa': discord.Color.from_rgb(255, 105, 180),
        'purple': discord.Color.purple(), 'roxo': discord.Color.purple(),
        'orange': discord.Color.orange(), 'laranja': discord.Color.orange(),
        'black': discord.Color.from_rgb(1, 1, 1), 'preto': discord.Color.from_rgb(1, 1, 1),
        'white': discord.Color.from_rgb(255, 255, 255), 'branco': discord.Color.from_rgb(255, 255, 255)
    }
    return mapa.get(c, discord.Color.default())

def encontrar_cargo(guild, busca):
    if not busca: return None
    busca = busca.strip()
    if busca.startswith("<@&") and busca.endswith(">"):
        id_cargo = int("".join(filter(str.isdigit, busca)))
        return guild.get_role(id_cargo)
    for r in guild.roles:
        if r.name.lower() == busca.lower(): return r
    return None

def normalizar_nome_canal(busca):
    if not busca:
        return ""
    nome = busca.strip()
    if nome.startswith("<#") and nome.endswith(">"):
        return nome
    if nome.startswith("#"):
        nome = nome[1:]
    return nome.strip().lower().replace(" ", "-")

def encontrar_canal_texto(guild, busca):
    if not guild or not busca:
        return None

    busca = busca.strip()
    if busca.startswith("<#") and busca.endswith(">"):
        id_canal = int("".join(filter(str.isdigit, busca)))
        canal = guild.get_channel(id_canal)
        return canal if isinstance(canal, discord.TextChannel) else None

    nome_normalizado = normalizar_nome_canal(busca)
    for canal in guild.text_channels:
        if canal.name.lower() == nome_normalizado:
            return canal
    return None

def encontrar_categoria(guild, busca):
    if not guild or not busca:
        return None

    nome_normalizado = busca.strip().lower()
    for categoria in guild.categories:
        if categoria.name.lower() == nome_normalizado:
            return categoria
    return None

def desserializar_texto_cmd(texto):
    if not texto:
        return ""
    return (
        texto.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\|", "|")
    ).strip()

def aplicar_emoji_no_nome_canal(nome_canal, emoji):
    nome_base = nome_canal.strip()
    if " " in nome_base:
        primeira_parte, restante = nome_base.split(" ", 1)
        if any(not ch.isalnum() and ch not in "-_" for ch in primeira_parte):
            nome_base = restante.strip()
    return f"{emoji}-{nome_base}".strip().lower().replace(" ", "-")

async def buscar_mensagem_em_canal(canal, mensagem_id):
    if not canal or not mensagem_id:
        return None
    try:
        return await canal.fetch_message(int(mensagem_id))
    except Exception:
        return None

ALIASES_CMD = {
    "ADICIONAR_EMOJI_CANAL": "EMOJI_CANAL",
    "MUDAR_EMOJI_CANAL": "EMOJI_CANAL",
    "ENVIAR_MENSAGEM_CANAL": "ENVIAR_MENSAGEM_CANAL",
    "EDITAR_MENSAGEM_CANAL": "EDITAR_MENSAGEM_CANAL",
    "APAGAR_MENSAGEM_CANAL": "APAGAR_MENSAGEM_CANAL",
    "RENOMEAR_CANAL": "RENOMEAR_CANAL",
    "MOVER_CANAL": "MOVER_CANAL",
    "SALVAR_TEMPLATE": "SALVAR_TEMPLATE",
    "ENVIAR_TEMPLATE": "ENVIAR_TEMPLATE",
    "CONSULTAR_REGISTRO_PERSONAGEM": "CONSULTAR_REGISTRO_PERSONAGEM",
}

def extrair_linha_comando(linha):
    texto = linha.strip()
    if not texto:
        return None
    if "CMD:" in texto:
        return texto[texto.find("CMD:"):]

    prefixo = texto.split("|", 1)[0].strip().upper()
    if prefixo in ALIASES_CMD:
        resto = texto[len(prefixo):]
        return f"CMD:{ALIASES_CMD[prefixo]}{resto}"
    return None

@bot.tree.command(name="dar_vip", description="Concede ou renova um cargo VIP por uma quantidade de dias")
@app_commands.describe(
    membro="Pessoa que recebera o VIP",
    cargo="Cargo VIP ja existente no servidor",
    dias="Quantidade de dias do VIP (de 1 a 3650)",
)
@app_commands.default_permissions(administrator=True)
async def dar_vip(interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role, dias: int):
    """Alternativa em comando de barra ao DAR_VIP do !zomboid."""
    if await bloquear_se_nao_for_staff(interaction):
        return
    if not interaction.guild or not interaction.channel:
        return await interaction.response.send_message("Este comando so funciona dentro de um servidor.", ephemeral=True)
    if not 1 <= dias <= 3650:
        return await interaction.response.send_message("Informe uma quantidade entre 1 e 3650 dias.", ephemeral=True)
    if cargo == interaction.guild.default_role or cargo.managed:
        return await interaction.response.send_message("Escolha um cargo VIP comum, nao @everyone nem um cargo gerenciado.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    ja_possui_cargo = cargo in membro.roles
    try:
        vencimento = await conceder_vip_temporario(
            interaction.guild, membro, cargo, dias, "dias", interaction.channel.id,
            f"VIP concedido por {interaction.user} via /dar_vip",
        )
    except discord.Forbidden:
        return await interaction.followup.send(
            "Nao consegui dar esse cargo. Deixe o cargo do bot acima do cargo VIP e habilite Gerenciar cargos.",
            ephemeral=True,
        )
    except discord.HTTPException as erro:
        return await interaction.followup.send(f"Falha ao conceder o VIP: `{erro}`", ephemeral=True)

    await interaction.followup.send(
        f"VIP **{cargo.name}** {'renovado' if ja_possui_cargo else 'concedido'} a {membro.mention} por **{dias} dia(s)**. "
        f"Expira em <t:{int(vencimento.timestamp())}:F>.",
        ephemeral=True,
    )

@bot.tree.command(name="criar_sorteio", description="🎉 Cria um sorteio com reações automáticas")
@app_commands.describe(titulo="Título do sorteio", subtitulo="Descrição do prêmio", minutos="Duração em minutos", emoji="Emoji da reação (padrão 🎉)", cargo_premio="Cargo VIP para o ganhador (opcional)")
@app_commands.default_permissions(administrator=True)
async def criar_sorteio(interaction: discord.Interaction, titulo: str, subtitulo: str, minutos: int, emoji: str = "🎉", cargo_premio: discord.Role = None):
    await interaction.response.defer(ephemeral=True)
    fim = datetime.now() + timedelta(minutes=minutos)
    
    texto_cargo = f" **Prêmio Automático:** {cargo_premio.mention}" if cargo_premio else " **Prêmio:** (Definido na descrição)"
    embed = discord.Embed(title=titulo, description=f"{subtitulo}\n\n{texto_cargo}\n **Termina em:** <t:{int(fim.timestamp())}:R>\n\n👇 **Reaja com {emoji} nesta mensagem para participar!**", color=discord.Color.gold())
    
    try:
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction(emoji)
    except Exception as e:
        await interaction.followup.send(f" Erro ao enviar mensagem ou adicionar emoji. Verifique se o emoji é válido. ({e})", ephemeral=True)
        return

    sorteios = carregar_sorteios()
    sorteios[str(msg.id)] = {
        "canal_id": interaction.channel.id,
        "guild_id": interaction.guild.id,
        "fim": fim.isoformat(),
        "emoji": emoji,
        "cargo_id": cargo_premio.id if cargo_premio else None,
        "titulo": titulo
    }
    salvar_sorteios(sorteios)
    await interaction.followup.send("✅ Sorteio criado e agendado com sucesso!", ephemeral=True)

@bot.tree.command(name="lista_sorteios", description="📋 Lista os sorteios ativos no servidor")
@app_commands.default_permissions(administrator=True)
async def lista_sorteios(interaction: discord.Interaction):
    sorteios = carregar_sorteios()
    if not sorteios: return await interaction.response.send_message(" Nenhum sorteio ativo no momento.", ephemeral=True)
    
    texto = "**📋 Sorteios Ativos:**\n"
    for msg_id, dados in sorteios.items():
        dt_fim = datetime.fromisoformat(dados['fim'])
        texto += f"• **{dados['titulo']}** termina em <t:{int(dt_fim.timestamp())}:R> (Canal: <#{dados['canal_id']}>)\n"
    await interaction.response.send_message(texto, ephemeral=True)

@bot.tree.command(name="refazer_sorteio", description="Sorteia de novo usando a mesma mensagem e reacoes")
@app_commands.describe(
    mensagem="Link da mensagem original do sorteio",
    emoji="Emoji usado para participar (opcional; o bot detecta sozinho)",
)
@app_commands.default_permissions(administrator=True)
async def refazer_sorteio(interaction: discord.Interaction, mensagem: str, emoji: str = ""):
    """Escolhe novo ganhador da reacao de um painel que ja terminou."""
    if await bloquear_se_nao_for_staff(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    ids_link = re.findall(r"\d{15,22}", mensagem)
    if len(ids_link) < 3:
        return await interaction.followup.send(
            "Envie o **link da mensagem** do painel do sorteio (Copiar link da mensagem).",
            ephemeral=True,
        )

    guild_id, canal_id, mensagem_id = map(int, ids_link[-3:])
    if not interaction.guild or guild_id != interaction.guild.id:
        return await interaction.followup.send("O link precisa ser de uma mensagem deste servidor.", ephemeral=True)

    canal = interaction.guild.get_channel(canal_id)
    if not canal or not hasattr(canal, "fetch_message"):
        return await interaction.followup.send("Nao encontrei o canal informado no link.", ephemeral=True)
    try:
        painel = await canal.fetch_message(mensagem_id)
    except discord.NotFound:
        return await interaction.followup.send("Nao encontrei a mensagem original do sorteio.", ephemeral=True)
    except discord.Forbidden:
        return await interaction.followup.send("O bot nao tem permissao para ler essa mensagem.", ephemeral=True)

    # A reacao oficial e a que o proprio bot adicionou ao criar o painel.
    # Quando nenhum emoji e informado, isso evita falha por confundir 🎉 e 🎊.
    emoji = emoji.strip()
    reacao_oficial = (
        discord.utils.find(lambda reacao: str(reacao.emoji) == emoji, painel.reactions)
        if emoji else discord.utils.find(lambda reacao: reacao.me, painel.reactions)
    )
    if not reacao_oficial:
        emojis_disponiveis = ", ".join(str(reacao.emoji) for reacao in painel.reactions) or "nenhum"
        return await interaction.followup.send(
            f"Nao encontrei a reacao do sorteio. Reacoes disponiveis: {emojis_disponiveis}.", ephemeral=True,
        )

    participantes_brutos = [user async for user in reacao_oficial.users()]
    participantes = participantes_elegiveis_sorteio(interaction.guild, participantes_brutos)
    excluidos = len(participantes_brutos) - len(participantes)
    if not participantes:
        return await interaction.followup.send(
            "Nao ha participantes elegiveis: bots, administradores e staff nao entram no sorteio.",
            ephemeral=True,
        )

    ganhador = random.choice(participantes)
    titulo = painel.embeds[0].title if painel.embeds and painel.embeds[0].title else "Sorteio"
    await canal.send(
        f"🎉 **NOVO RESULTADO — {titulo}**\n"
        f"{ganhador.mention} ganhou o novo sorteio! "
        f"(Participantes elegiveis: {len(participantes)}; staff/bots excluidos: {excluidos}.)"
    )
    await interaction.followup.send(
        f"Novo ganhador escolhido: {ganhador.mention}. Usei a mesma reacao da mensagem original.",
        ephemeral=True,
    )

@bot.tree.command(name="adduser", description="Cria jogador direto no painel")
@app_commands.describe(nome="Nome do jogador", senha="Senha do jogador")
@app_commands.default_permissions(administrator=True)
async def cmd_adduser(interaction: discord.Interaction, nome: str, senha: str):
    await interaction.response.defer()
    comando = f'adduser "{nome}" "{senha}"'
    resposta = await enviar_comando_rcon(comando)
    await interaction.followup.send(f"💻 **Comando enviado:** `{comando}`\n**Console retornou:**\n```\n{resposta}\n```")

@bot.tree.command(name="forcar_morte", description=" 💀 Registra manualmente a morte de um player")
@app_commands.default_permissions(administrator=True)
async def forcar_morte(interaction: discord.Interaction, nome_personagem: str):
    status_db = carregar_status()
    nome_limpo = normalizar_chave_personagem(nome_personagem)
    status_db[nome_limpo] = "morto"
    salvar_status(status_db)
    await interaction.response.send_message(f"💀 **{nome_personagem}** marcado como MORTO.", ephemeral=True)

@bot.tree.command(name="aprovar_ficha", description="✅ (ADMIN) Ignora o banco de mortes e força a aprovação")
@app_commands.default_permissions(administrator=True)
async def aprovar_ficha(interaction: discord.Interaction):
    await interaction.response.defer()

    # 1) Ficha em analise agora (digitada ou vinda do Modal): cancela a espera
    #    dos 3 minutos e aprova na hora.
    analise = next(
        (a for a in carregar_fichas_em_analise() if a.get("canal_id") == interaction.channel.id),
        None,
    )
    if analise:
        try:
            alvo = await reconstruir_ficha_salva(interaction.channel, analise)
            await cancelar_processamento_ficha(analise.get("canal_id"), analise.get("msg_id"))
            remover_ficha_em_analise(analise.get("canal_id"), analise.get("msg_id"))

            msg_espera = await buscar_mensagem_em_canal(interaction.channel, analise.get("msg_espera_id"))
            if msg_espera:
                with suppress(Exception):
                    await msg_espera.delete()

            await interaction.followup.send("⚙ **Modo Admin:** Cancelando a espera e forçando aprovação instantânea...")
            agendar_processamento_ficha(alvo, bypass=True, checar_online=False)
            return
        except Exception as erro:
            print(f"[FICHAS] Falha ao aprovar ficha em analise: {erro}")

    # 2) Ficha guardada na fila duravel: esperando a abertura agendada ou o
    #    servidor subir. E aqui que ela fica hoje, inclusive a vinda do Modal.
    entrada = next(
        (p for p in carregar_fila_registro() if p.get("canal_id") == interaction.channel.id),
        None,
    )
    if entrada:
        try:
            alvo = await reconstruir_ficha_salva(interaction.channel, entrada)
            await cancelar_processamento_ficha(entrada.get("canal_id"), entrada.get("msg_id"))

            estado = entrada.get("estado")
            if estado == ESTADO_AGUARDANDO_STAFF:
                motivo = "estava aguardando aprovação manual da staff"
            elif estado == ESTADO_AGUARDANDO_ABERTURA:
                motivo = "estava guardada esperando o horário de abertura"
            elif estado == ESTADO_AGUARDANDO_SERVIDOR:
                motivo = "estava na fila esperando o servidor"
            else:
                motivo = "estava na fila de registro"

            await interaction.followup.send(
                f"⚙ **Modo Admin:** a ficha {motivo}. Ignorando horário, servidor e anti-fraude — aprovando agora..."
            )
            agendar_processamento_ficha(alvo, bypass=True, checar_online=False)
            return
        except Exception as erro:
            print(f"[FICHAS] Falha ao aprovar ficha da fila: {erro}")

    # 3) Sem nada guardado: procura uma ficha digitada nas ultimas mensagens.
    async for msg in interaction.channel.history(limit=15):
        if mensagem_parece_formulario_ficha(msg) and msg.author != bot.user:
            await interaction.followup.send("⚙ **Modo Admin:** Ignorando banco de dados e forçando aprovação instantânea...")
            agendar_processamento_ficha(msg, bypass=True, checar_online=False)
            return

    await interaction.followup.send(
        "❌ Não encontrei nenhuma ficha neste ticket — nem em análise, nem na fila, nem nas últimas 15 mensagens. "
        "*Peça para o jogador enviar a ficha primeiro.*"
    )

@bot.tree.command(name="tempo_fechar_ticket", description="🗑 Define em quantos minutos o ticket some depois do registro")
@app_commands.describe(
    minutos="Minutos até o ticket ser apagado após o registro concluído.",
    desativar="Se marcado, o ticket NUNCA é apagado sozinho.",
)
@app_commands.default_permissions(administrator=True)
async def tempo_fechar_ticket(interaction: discord.Interaction, minutos: int = None, desativar: bool = False):
    if await bloquear_se_nao_for_staff(interaction):
        return

    atual = minutos_fechar_ticket()
    na_fila = len(carregar_tickets_para_fechar())

    # Sem argumentos: mostra a configuração atual.
    if minutos is None and not desativar:
        embed = discord.Embed(title="🗑 Fechamento Automático de Tickets", color=discord.Color.blurple())
        if atual:
            embed.description = f"Os tickets de personagem somem **{atual} minuto(s)** depois do registro concluído."
        else:
            embed.color = discord.Color.orange()
            embed.description = "🔕 **Desativado.** Os tickets ficam abertos até alguém fechar."
        embed.add_field(name="Aguardando fechamento agora", value=f"**{na_fila}** ticket(s)", inline=True)
        embed.set_footer(text="Use minutos: para alterar, ou desativar:True para nunca apagar.")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    if desativar:
        salvar_config_tickets({
            "desativado": True,
            "alterado_em": datetime.now().isoformat(),
            "alterado_por": str(interaction.user),
        })
        salvar_tickets_para_fechar([])
        return await interaction.response.send_message(
            "🔕 **Fechamento automático desativado.**\n"
            "Os tickets de personagem vão ficar abertos até alguém usar o botão **🗑 Fechar Ticket** ou `/fechar_ticket`.\n"
            f"*Os {na_fila} ticket(s) que estavam na fila de fechamento foram poupados.*",
            ephemeral=True,
        )

    if minutos < 1:
        return await interaction.response.send_message(
            "❌ Use no mínimo **1** minuto. Para nunca apagar, use `desativar:True`.", ephemeral=True)
    if minutos > 10080:
        return await interaction.response.send_message("❌ Máximo de **10080** minutos (7 dias).", ephemeral=True)

    salvar_config_tickets({
        "minutos": minutos,
        "desativado": False,
        "alterado_em": datetime.now().isoformat(),
        "alterado_por": str(interaction.user),
    })

    anterior = f"**{atual}** minuto(s)" if atual else "**desativado**"
    embed = discord.Embed(
        title="🗑 Tempo de Fechamento Atualizado",
        description=f"De {anterior} para **{minutos}** minuto(s).",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="Como funciona",
        value=(
            "A contagem começa quando o registro é **concluído com sucesso**. "
            "Ticket recusado ou esperando a abertura não é apagado.\n"
            "O prazo fica gravado em disco, então vale mesmo se o bot reiniciar no meio."
        ),
        inline=False,
    )
    if na_fila:
        embed.add_field(
            name="Atenção",
            value=f"**{na_fila}** ticket(s) já estavam agendados com o tempo antigo e mantêm o prazo anterior.",
            inline=False,
        )
    embed.set_footer(text=f"Alterado por {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="aprovacao_automatica", description="🤖 Liga/desliga a aprovação automática de fichas de personagem")
@app_commands.describe(
    ativar="True = o bot cria o personagem sozinho. False = só a staff libera, com /aprovar_ficha.",
)
@app_commands.default_permissions(administrator=True)
async def aprovacao_automatica(interaction: discord.Interaction, ativar: bool = None):
    if await bloquear_se_nao_for_staff(interaction):
        return

    ativa_agora = aprovacao_automatica_ativa()
    fila = carregar_fila_registro()
    aguardando_staff = [p for p in fila if p.get("estado") == ESTADO_AGUARDANDO_STAFF]

    # Sem argumento: mostra a situação.
    if ativar is None:
        embed = discord.Embed(title="🤖 Aprovação de Fichas", color=discord.Color.blurple())
        if ativa_agora:
            embed.color = discord.Color.green()
            embed.description = (
                "✅ **Automática (ligada).**\n"
                "O bot analisa e cria o personagem sozinho assim que a ficha chega."
            )
        else:
            embed.color = discord.Color.orange()
            embed.description = (
                "🙋 **Manual (desligada).**\n"
                "As fichas são recebidas e guardadas, mas só viram personagem quando a staff usar `/aprovar_ficha` no ticket."
            )
        embed.add_field(name="Esperando a staff", value=f"**{len(aguardando_staff)}** ficha(s)", inline=True)
        embed.add_field(name="Total na fila", value=f"**{len(fila)}**", inline=True)
        embed.set_footer(text="Use ativar:True ou ativar:False para mudar.")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    if ativar == ativa_agora:
        estado = "ligada" if ativa_agora else "desligada"
        return await interaction.response.send_message(
            f"ℹ A aprovação automática já está **{estado}**. Nada mudou.", ephemeral=True)

    definir_aprovacao_automatica(ativar, interaction.user)

    if ativar:
        embed = discord.Embed(
            title="✅ Aprovação Automática LIGADA",
            description="O bot volta a analisar e criar os personagens sozinho.",
            color=discord.Color.green(),
        )
        if aguardando_staff:
            embed.add_field(
                name="Fichas represadas",
                value=f"**{len(aguardando_staff)}** ficha(s) que esperavam a staff vão ser processadas agora.",
                inline=False,
            )
        if not registros_estao_liberados():
            embed.add_field(
                name="⚠ Atenção",
                value=f"Ainda existe abertura agendada: {texto_abertura_discord()} Até lá nada é criado.",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)
        bot.loop.create_task(processar_fichas_pendentes(espera_estabilizacao=False))
        return

    embed = discord.Embed(
        title="🙋 Aprovação Automática DESLIGADA",
        description=(
            "As fichas continuam sendo **recebidas e guardadas em disco**, mas nenhum personagem "
            "é criado sozinho.\n\n"
            "Para liberar, entre no ticket e use **`/aprovar_ficha`**."
        ),
        color=discord.Color.orange(),
    )
    embed.add_field(
        name="O que o jogador vê",
        value="Ele recebe a confirmação de que a ficha foi recebida e que a staff vai analisar.",
        inline=False,
    )
    embed.set_footer(text=f"Desligado por {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="agendar_abertura", description="🗓 Marca a data/hora em que a aprovação de personagens começa")
@app_commands.describe(
    hora="Hora de início, ex: 20:00 (horário de Brasília)",
    data="Data, ex: 07/08/2026. Se não informar, usa hoje (ou amanhã se a hora já passou).",
    cancelar="Libera os registros imediatamente e remove o agendamento.",
)
@app_commands.default_permissions(administrator=True)
async def agendar_abertura(interaction: discord.Interaction, hora: str = None, data: str = None, cancelar: bool = False):
    if await bloquear_se_nao_for_staff(interaction):
        return

    fila = carregar_fila_registro()
    aguardando = [p for p in fila if p.get("estado") == ESTADO_AGUARDANDO_ABERTURA]

    if cancelar:
        tinha = timestamp_abertura_registros()
        salvar_config_abertura({
            "liberado_em": datetime.now().isoformat(),
            "liberado_por": str(interaction.user),
        })

        if not tinha:
            return await interaction.response.send_message("ℹ Não havia agendamento — os registros já estavam abertos.", ephemeral=True)

        await interaction.response.send_message(
            f"🔓 **Registros liberados agora!**\n"
            f"**{len(aguardando)}** ficha(s) que estavam guardadas vão começar a ser processadas em instantes."
        )
        # Sem os 5 minutos de estabilizacao: a liberacao foi manual e imediata.
        bot.loop.create_task(processar_fichas_pendentes(espera_estabilizacao=False))
        return

    # Sem argumentos: mostra a situação atual.
    if not hora and not data:
        embed = discord.Embed(title="🗓 Abertura dos Registros", color=discord.Color.blurple())
        momento = timestamp_abertura_registros()
        if momento is None:
            embed.color = discord.Color.green()
            embed.description = "✅ **Os registros estão abertos.** As fichas são aprovadas assim que chegam."
        else:
            embed.description = texto_abertura_discord()
            embed.add_field(name="Fichas guardadas esperando", value=f"**{len(aguardando)}**", inline=True)
        embed.add_field(name="Total na fila", value=f"**{len(fila)}**", inline=True)
        embed.set_footer(text="Use hora: e data: para agendar, ou cancelar:True para liberar já.")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    momento_local, erro = interpretar_data_hora(data, hora)
    if erro:
        return await interaction.response.send_message(f"❌ {erro}", ephemeral=True)

    epoch = epoch_de_horario_local(momento_local)
    if epoch <= time.time():
        return await interaction.response.send_message(
            f"❌ Esse horário já passou (<t:{int(epoch)}:F>). Informe um momento no futuro.", ephemeral=True)

    # Agendamento novo SUBSTITUI o anterior por completo: o arquivo e reescrito
    # do zero, sem herdar nada da marcacao antiga.
    anterior = timestamp_abertura_registros()
    salvar_config_abertura({
        "abertura_epoch": epoch,
        "agendado_em": datetime.now().isoformat(),
        "agendado_por": str(interaction.user),
        "substituiu_epoch": anterior,
    })

    marca = int(epoch)
    embed = discord.Embed(
        title="🗓 Abertura Agendada",
        description=f"A aprovação de personagens começa <t:{marca}:F>\n(<t:{marca}:R>)",
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="Até lá",
        value=(
            "Os jogadores **podem abrir ticket e mandar a ficha normalmente**. "
            "O bot valida nome e senha na hora e guarda tudo em disco.\n"
            "Nenhum personagem é criado antes do horário marcado."
        ),
        inline=False,
    )
    if anterior:
        embed.add_field(
            name="♻ Agendamento anterior",
            value=f"<t:{int(anterior)}:F> foi **apagado** e não vale mais.",
            inline=False,
        )
    if aguardando or fila:
        embed.add_field(name="Já guardadas", value=f"**{len(aguardando)}** ficha(s) esperando a abertura", inline=True)
    embed.set_footer(text=f"Agendado por {interaction.user.display_name} · horário de Brasília")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="versao_bot", description="ℹ Mostra a versão instalada e se existe atualização no GitHub")
@app_commands.default_permissions(administrator=True)
async def versao_bot(interaction: discord.Interaction):
    if await bloquear_se_nao_for_staff(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    local = carregar_versao_bot()
    remoto, erro = await consultar_ultimo_commit()

    embed = discord.Embed(title="ℹ Versão do Bot", color=discord.Color.blurple())
    embed.add_field(name="Repositório", value=f"`{REPO_GITHUB}` (branch `{BRANCH_GITHUB}`)", inline=False)

    if local.get("sha"):
        embed.add_field(
            name="Instalada agora",
            value=f"`{local['sha'][:7]}` — {local.get('mensagem') or 'sem descrição'}\n*Atualizado em {formatar_data_registro(local.get('atualizado_em'))}*",
            inline=False,
        )
    else:
        embed.add_field(name="Instalada agora", value="Desconhecida (nunca atualizada pelo comando)", inline=False)

    if erro:
        embed.color = discord.Color.orange()
        embed.add_field(name="⚠ GitHub", value=erro, inline=False)
    else:
        embed.add_field(
            name="Última no GitHub",
            value=f"`{remoto['sha'][:7]}` — {remoto['mensagem']}\n*por {remoto['autor']}*",
            inline=False,
        )
        if local.get("sha") == remoto["sha"]:
            embed.color = discord.Color.green()
            embed.add_field(name="Situação", value="✅ O bot está atualizado.", inline=False)
        else:
            embed.color = discord.Color.gold()
            embed.add_field(name="Situação", value="🆕 Existe atualização. Use `/bot_atualizar`.", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="bot_atualizar", description="⬆ Baixa a última versão do GitHub e reinicia o bot")
@app_commands.describe(
    apenas_verificar="Só mostra o que mudaria, sem aplicar nada.",
    forcar="Reinstala mesmo se já estiver na última versão.",
)
@app_commands.default_permissions(administrator=True)
async def bot_atualizar(interaction: discord.Interaction, apenas_verificar: bool = False, forcar: bool = False):
    if await bloquear_se_nao_for_staff(interaction):
        return

    await interaction.response.defer()

    local = carregar_versao_bot()
    remoto, erro = await consultar_ultimo_commit()
    if erro:
        return await interaction.followup.send(f"❌ **Não consegui consultar o GitHub:** {erro}")

    ja_atualizado = local.get("sha") == remoto["sha"]
    if ja_atualizado and not forcar and not apenas_verificar:
        return await interaction.followup.send(
            f"✅ **O bot já está na última versão** (`{remoto['sha'][:7]}` — {remoto['mensagem']}).\n"
            f"*Use `forcar:True` se quiser reinstalar mesmo assim.*"
        )

    arquivos, erro = await listar_arquivos_repo(remoto["sha"])
    if erro:
        return await interaction.followup.send(f"❌ {erro}")
    if not arquivos:
        return await interaction.followup.send("❌ Nenhum arquivo de código encontrado no repositório.")

    # Estado em disco que vai sobreviver ao reinicio (nada disso e tocado).
    fila = carregar_fila_registro()
    analises = carregar_fichas_em_analise()

    if apenas_verificar:
        embed = discord.Embed(
            title="🔎 Verificação de Atualização",
            description=("🆕 Existe uma versão nova." if not ja_atualizado else "✅ Já está na última versão."),
            color=discord.Color.gold() if not ja_atualizado else discord.Color.green(),
        )
        embed.add_field(name="Instalada", value=f"`{(local.get('sha') or 'desconhecida')[:7]}`", inline=True)
        embed.add_field(name="No GitHub", value=f"`{remoto['sha'][:7]}`", inline=True)
        embed.add_field(name="Mudança", value=remoto["mensagem"] or "—", inline=False)
        embed.add_field(name="Arquivos que seriam trocados", value="```" + "\n".join(arquivos[:20]) + "```", inline=False)
        embed.add_field(
            name="🔒 Preservado (nunca tocado)",
            value=f"Todos os `.json` e o `.env`.\nNa fila: **{len(fila)}** ficha(s), **{len(analises)}** em análise.",
            inline=False,
        )
        return await interaction.followup.send(embed=embed)

    msg = await interaction.followup.send(
        f"⬇ **Baixando a versão `{remoto['sha'][:7]}`** ({len(arquivos)} arquivo(s))...", wait=True
    )

    # 1) Baixa tudo primeiro e valida ANTES de gravar qualquer coisa.
    baixados = {}
    for caminho_repo in arquivos:
        conteudo, erro = await baixar_arquivo_repo(caminho_repo, remoto["sha"])
        if erro:
            return await msg.edit(content=f"❌ **Atualização cancelada:** {erro}\n*Nada foi alterado.*")

        if caminho_repo.lower().endswith(".py"):
            problema = validar_codigo_python(conteudo, caminho_repo)
            if problema:
                return await msg.edit(content=f"❌ **Atualização cancelada:** {problema}\n*Nada foi alterado — o bot continua rodando na versão atual.*")

        baixados[caminho_repo] = conteudo

    # 2) Backup e gravacao.
    await msg.edit(content=f"💾 **Código validado.** Fazendo backup e aplicando {len(baixados)} arquivo(s)...")
    try:
        preparar_pasta_backup()
        requirements_mudou = False

        for caminho_repo, conteudo in baixados.items():
            destino = os.path.join(BASE_DIR, caminho_repo.replace("/", os.sep))

            if os.path.exists(destino):
                with open(destino, "rb") as f:
                    if f.read() == conteudo:
                        continue
            salvar_backup_arquivo(destino)

            os.makedirs(os.path.dirname(destino), exist_ok=True)
            temporario = destino + ".novo"
            with open(temporario, "wb") as f:
                f.write(conteudo)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporario, destino)

            if os.path.basename(caminho_repo).lower() == "requirements.txt":
                requirements_mudou = True
    except Exception as falha:
        restaurados = restaurar_backup()
        return await msg.edit(content=f"❌ **Falha ao gravar:** {falha}\n🔄 Restaurei {restaurados} arquivo(s) do backup. O bot segue na versão antiga.")

    # 3) Dependencias novas, se houver.
    if requirements_mudou:
        await msg.edit(content="📦 **`requirements.txt` mudou.** Instalando dependências... *(pode demorar)*")
        erro_pip = await asyncio.to_thread(instalar_dependencias)
        if erro_pip:
            restaurados = restaurar_backup()
            return await msg.edit(content=f"❌ **Falha ao instalar dependências:**\n```{erro_pip}```\n🔄 Restaurei {restaurados} arquivo(s). O bot segue na versão antiga.")

    salvar_versao_bot({
        "sha": remoto["sha"],
        "mensagem": remoto["mensagem"],
        "autor": remoto["autor"],
        "atualizado_em": datetime.now().isoformat(),
        "atualizado_por": str(interaction.user),
    })

    embed = discord.Embed(
        title="✅ Atualização Aplicada — Reiniciando",
        description=f"**{remoto['mensagem']}**\n`{(local.get('sha') or '???')[:7]}` ➜ `{remoto['sha'][:7]}`",
        color=discord.Color.green(),
    )
    embed.add_field(name="Arquivos trocados", value=f"`{len(baixados)}`", inline=True)
    embed.add_field(name="Aplicado por", value=interaction.user.mention, inline=True)
    embed.add_field(
        name="🔒 Dados preservados",
        value=(
            "Nenhum `.json` ou `.env` foi tocado.\n"
            f"**{len(fila)}** ficha(s) na fila e **{len(analises)}** em análise continuam garantidas — "
            "o bot retoma tudo assim que voltar."
        ),
        inline=False,
    )
    embed.set_footer(text="O bot volta em alguns segundos.")
    await msg.edit(content=None, embed=embed)

    print(f"[UPDATE] Atualizado para {remoto['sha']} por {interaction.user}. Reiniciando...")
    await asyncio.sleep(2)

    with suppress(Exception):
        await bot.close()
    reiniciar_processo_bot()

@bot.tree.command(name="diagnostico_mortes", description="🔎 Mostra o arquivo de mortes que o bot está lendo e como ele interpreta as linhas")
@app_commands.describe(linhas="Quantas linhas finais mostrar (padrão 5)")
@app_commands.default_permissions(administrator=True)
async def diagnostico_mortes(interaction: discord.Interaction, linhas: int = 5):
    if await bloquear_se_nao_for_staff(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    linhas = max(1, min(15, linhas))

    caminhos = await asyncio.to_thread(caminhos_mortes_friendhost)

    embed = discord.Embed(title="🔎 Diagnóstico de Detecção de Mortes", color=discord.Color.blurple())
    embed.add_field(name="Caminho configurado", value=f"```{CAMINHO_MORTES}```", inline=False)

    if not caminhos:
        embed.color = discord.Color.red()
        embed.add_field(
            name="❌ Nenhum arquivo encontrado",
            value=(
                f"O bot procurou em:\n```{CSV_BASE_PATH}```\n"
                "Sem esse arquivo o **anti-fraude não detecta morte nenhuma**.\n"
                "Corrija com `CAMINHO_MOD_MORTES=` ou `CSV_BASE_PATH=` no `.env`."
            ),
            inline=False,
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    embed.add_field(
        name=f"✅ {len(caminhos)} arquivo(s) encontrado(s)",
        value="```" + "\n".join(caminhos[:5]) + "```",
        inline=False,
    )

    principal = caminhos[0]
    try:
        conteudo = await asyncio.to_thread(ler_final_arquivo, principal)
        ultimas = [linha for linha in conteudo.splitlines() if linha.strip()][-linhas:]
    except Exception as erro:
        embed.color = discord.Color.red()
        embed.add_field(name="❌ Erro ao ler", value=f"```{erro}```", inline=False)
        return await interaction.followup.send(embed=embed, ephemeral=True)

    if not ultimas:
        embed.add_field(name="⚠ Arquivo vazio", value="Ainda não morreu ninguém, ou o mod não está gravando aqui.", inline=False)
        return await interaction.followup.send(embed=embed, ephemeral=True)

    bruto = "\n".join(linha[:180] for linha in ultimas)
    embed.add_field(name="Últimas linhas (bruto)", value=f"```{bruto[:1000]}```", inline=False)

    leitura = []
    for linha in ultimas:
        nomes = nomes_na_linha_morte(linha)
        if nomes:
            leitura.append(f"✅ {', '.join(nomes)}")
        else:
            leitura.append("❌ nenhum nome reconhecido" + ("" if linha_indica_morte(linha) else " (sem marcador de morte)"))

    reconhecidas = sum(1 for item in leitura if item.startswith("✅"))
    embed.add_field(name="Como o bot interpretou", value="```" + "\n".join(leitura)[:1000] + "```", inline=False)

    if reconhecidas == 0:
        embed.color = discord.Color.red()
        embed.add_field(
            name="🚨 Formato não reconhecido",
            value="O bot achou o arquivo mas **não consegue extrair os nomes**. O anti-fraude não vai funcionar. Mande essas linhas para ajustar o parser.",
            inline=False,
        )
    elif reconhecidas < len(ultimas):
        embed.color = discord.Color.orange()
    else:
        embed.color = discord.Color.green()

    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="configurar_vidas", description="❤ Define quantas vidas (recriações) cada jogador tem na temporada")
@app_commands.describe(
    modo="Limitado = usa a quantidade informada. Ilimitado = sem limite de personagens.",
    quantidade="Quantas vezes o jogador pode RECRIAR o personagem (não conta o primeiro). Só para o modo Limitado.",
)
@app_commands.choices(modo=[
    app_commands.Choice(name="Limitado", value="limitado"),
    app_commands.Choice(name="Ilimitado (padrão)", value="ilimitado"),
])
@app_commands.default_permissions(administrator=True)
async def configurar_vidas(interaction: discord.Interaction, modo: app_commands.Choice[str] = None, quantidade: int = None):
    if await bloquear_se_nao_for_staff(interaction):
        return

    config = carregar_config_vidas()

    # Sem argumentos: apenas mostra a configuração atual.
    if modo is None and quantidade is None:
        atual = "♾ Ilimitado" if config["ilimitado"] else f"`{config['limite_vidas']}` recriações por jogador"
        embed = discord.Embed(title="❤ Configuração de Vidas", color=discord.Color.blurple())
        embed.add_field(name="Modo atual", value=atual, inline=False)
        embed.add_field(name="Jogadores com vidas usadas", value=f"`{len(config['vidas_usadas'])}`", inline=True)
        embed.add_field(name="Jogadores com bônus", value=f"`{len(config['vidas_extras'])}`", inline=True)
        embed.set_footer(text="Use o parâmetro 'modo' para alterar.")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    valor_modo = modo.value if modo else ("limitado" if quantidade is not None else "ilimitado")

    if valor_modo == "ilimitado":
        config["ilimitado"] = True
        salvar_config_vidas(config)
        return await interaction.response.send_message(
            "♾ **Limite de vidas desativado.** Os jogadores podem criar quantos personagens quiserem "
            "(sempre respeitando a morte do anterior).\n"
            "*O histórico de vidas usadas foi mantido — se você religar o limite, ninguém volta do zero.*",
            ephemeral=True,
        )

    if quantidade is None:
        return await interaction.response.send_message(
            "❌ No modo **Limitado** você precisa informar a `quantidade` de vidas.", ephemeral=True)
    if quantidade < 0:
        return await interaction.response.send_message("❌ A quantidade não pode ser negativa.", ephemeral=True)

    anterior = "ilimitado" if config["ilimitado"] else str(config["limite_vidas"])
    config["ilimitado"] = False
    config["limite_vidas"] = quantidade
    salvar_config_vidas(config)

    embed = discord.Embed(
        title="❤ Limite de Vidas Atualizado",
        description=f"De **{anterior}** para **{quantidade}** recriação(ões) por jogador.",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="Como fica na prática",
        value=(
            f"Cada jogador pode ter **{quantidade + 1}** personagens no total desta temporada "
            f"(o primeiro + {quantidade} recriações)."
        ),
        inline=False,
    )
    embed.add_field(
        name="Ninguém foi resetado",
        value=(
            "O bot guarda quantas vidas cada um já **usou**, não quantas restam. "
            f"Quem já tinha gastado 1 vida agora fica com **{max(0, quantidade - 1)}** restantes; "
            f"quem não gastou nenhuma fica com **{quantidade}**."
        ),
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="adicionar_vidas", description="➕ Dá (ou tira) vidas extras de um jogador específico")
@app_commands.describe(
    jogador="Jogador do Discord (digite o nome ou use @)",
    quantidade="Quantas vidas adicionar. Use número negativo para tirar.",
)
@app_commands.default_permissions(administrator=True)
async def adicionar_vidas(interaction: discord.Interaction, jogador: discord.Member, quantidade: int):
    if await bloquear_se_nao_for_staff(interaction):
        return

    if quantidade == 0:
        return await interaction.response.send_message("❌ Informe um valor diferente de zero.", ephemeral=True)

    antes = calcular_vidas(jogador.id)
    depois = adicionar_vidas_extras(jogador.id, quantidade)

    embed = discord.Embed(
        title="❤ Vidas Ajustadas",
        description=f"{jogador.mention} recebeu **{quantidade:+d}** vida(s).",
        color=discord.Color.green() if quantidade > 0 else discord.Color.orange(),
    )

    if depois["ilimitado"]:
        embed.add_field(
            name="⚠ Atenção",
            value=(
                "A temporada está no modo **ilimitado**, então esse bônus não muda nada agora — "
                "mas fica guardado e passa a valer se você ativar o limite com `/configurar_vidas`."
            ),
            inline=False,
        )
    else:
        embed.add_field(name="Vidas restantes", value=f"`{antes['restantes']}` ➜ **`{depois['restantes']}`**", inline=True)
        embed.add_field(name="Já usadas", value=f"`{depois['usadas']}` de `{depois['total']}`", inline=True)
        embed.add_field(name="Bônus acumulado", value=f"`{depois['extras']:+d}`", inline=True)

    embed.set_footer(text=f"Ajustado por {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ver_vidas", description="👁 Consulta quantas vidas um jogador ainda tem")
@app_commands.describe(jogador="Jogador do Discord (digite o nome ou use @)")
@app_commands.default_permissions(administrator=True)
async def ver_vidas(interaction: discord.Interaction, jogador: discord.Member):
    if await bloquear_se_nao_for_staff(interaction):
        return

    vidas = calcular_vidas(jogador.id)
    personagem = carregar_personagens().get(str(jogador.id))

    embed = discord.Embed(title="❤ Vidas do Jogador", color=discord.Color.blurple())
    embed.add_field(name="Jogador", value=f"{jogador.mention}\n`{jogador.id}`", inline=False)
    embed.add_field(name="Personagem atual", value=f"```{personagem or 'nenhum'}```", inline=False)

    if vidas["ilimitado"]:
        embed.add_field(name="Situação", value="♾ Temporada com vidas **ilimitadas**", inline=False)
        embed.add_field(name="Recriações já feitas", value=f"`{vidas['usadas']}`", inline=True)
    else:
        embed.add_field(name="Vidas restantes", value=f"**`{vidas['restantes']}`** de `{vidas['total']}`", inline=True)
        embed.add_field(name="Já usadas", value=f"`{vidas['usadas']}`", inline=True)
        if vidas["extras"]:
            embed.add_field(name="Bônus da staff", value=f"`{vidas['extras']:+d}`", inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="fila_registros", description="📋 Mostra as fichas na fila esperando o servidor abrir")
@app_commands.default_permissions(administrator=True)
async def fila_registros(interaction: discord.Interaction):
    if await bloquear_se_nao_for_staff(interaction):
        return

    fila = carregar_fila_registro()
    if not fila:
        return await interaction.response.send_message("✅ A fila está vazia — nenhuma ficha aguardando registro.", ephemeral=True)

    rotulos = {
        ESTADO_AGUARDANDO_STAFF: "🙋 Aguardando aprovação da staff",
        ESTADO_AGUARDANDO_SERVIDOR: "⏳ Aguardando servidor",
        ESTADO_NA_FILA: "📤 Enviada para registro",
        ESTADO_REGISTRANDO: "⚡ Registrando agora",
    }

    embed = discord.Embed(
        title="📋 Fila de Registros",
        description=f"**{len(fila)}** ficha(s) guardada(s) em disco. Nenhuma é perdida se o bot reiniciar.",
        color=discord.Color.blurple(),
    )

    contagem = {}
    travadas = 0
    for p in fila:
        contagem[p.get("estado")] = contagem.get(p.get("estado"), 0) + 1
        if p.get("tentativas", 0) >= MAX_TENTATIVAS_REGISTRO:
            travadas += 1

    resumo = "\n".join(f"{rotulos.get(estado, estado)}: **{qtd}**" for estado, qtd in contagem.items())
    embed.add_field(name="Situação", value=resumo or "—", inline=False)

    if travadas:
        embed.add_field(name="⚠ Precisam da staff", value=f"**{travadas}** ficha(s) estouraram o limite de tentativas. Use `/aprovar_ficha` no ticket.", inline=False)

    linhas = []
    for p in fila[:12]:
        canal = interaction.guild.get_channel(p.get("canal_id"))
        alvo = canal.mention if canal else f"`canal {p.get('canal_id')}`"
        tentativas = p.get("tentativas", 0)
        extra = f" · {tentativas} tentativa(s)" if tentativas else ""
        linhas.append(f"<@{p.get('autor_id')}> — {alvo}{extra}")

    if linhas:
        if len(fila) > 12:
            linhas.append(f"*... e mais {len(fila) - 12}.*")
        embed.add_field(name="Jogadores na fila", value="\n".join(linhas), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="enviar_botao_fechar", description="🗑 Posta o botão de fechar ticket neste canal")
@app_commands.default_permissions(administrator=True)
async def enviar_botao_fechar(interaction: discord.Interaction):
    if await bloquear_se_nao_for_staff(interaction):
        return

    if not canal_e_ticket(interaction.channel):
        return await interaction.response.send_message(
            "❌ Este canal não parece um ticket. O botão só é enviado dentro de tickets.", ephemeral=True)

    await interaction.response.send_message("✅ Botão enviado neste canal.", ephemeral=True)
    await interaction.channel.send(
        "🗑 **Terminou seu atendimento?** Use o botão abaixo para fechar este ticket.\n"
        "*Se ainda precisa de ajuda, é só continuar conversando aqui.*",
        view=FecharTicketView(),
    )

@bot.tree.command(name="enviar_formulario", description="📝 Envia o botão do formulário de ficha neste canal")
@app_commands.describe(jogador="Dono do ticket (opcional). Usado para mostrar as vidas certas na mensagem.")
@app_commands.default_permissions(administrator=True)
async def enviar_formulario(interaction: discord.Interaction, jogador: discord.Member = None):
    if await bloquear_se_nao_for_staff(interaction):
        return
    await interaction.response.send_message("✅ Formulário enviado neste canal.", ephemeral=True)
    await enviar_painel_ficha(interaction.channel, jogador or interaction.user)

@bot.tree.command(name="historico_registro", description="📚 Consulta o último registro de personagem de um player")
@app_commands.describe(jogador="Jogador do Discord que você quer consultar")
@app_commands.default_permissions(administrator=True)
async def historico_registro(interaction: discord.Interaction, jogador: discord.Member):
    registros = carregar_registros_personagens()
    registro = registros.get(str(jogador.id))

    if not registro:
        return await interaction.response.send_message(f"Não encontrei nenhum registro salvo para {jogador.mention}.", ephemeral=True)

    embed = montar_embed_registro_personagem(interaction.guild, jogador, registro)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="criar_painel", description=" 🎨 Cria um painel customizável de ticket")
@app_commands.default_permissions(administrator=True)
async def criar_painel(interaction: discord.Interaction, titulo: str, subtitulo: str, texto_botao: str = "Abrir Ticket", emoji_botao: str = " 📩", categoria_ticket: str = "  🎫 ATENDIMENTO", mensagem_ticket: str = "Aguarde atendimento."):
    embed = discord.Embed(title=titulo, description=subtitulo, color=0x2ecc71)
    nome_server = interaction.guild.name
    icone_server = interaction.guild.icon.url if interaction.guild.icon else None
    embed.set_author(name=f"{nome_server} | Atendimento", icon_url=icone_server)
    view = TicketButton(texto_botao=texto_botao, emoji_botao=emoji_botao)
    try:
        await interaction.response.defer(ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=view)
        paineis = carregar_paineis()
        paineis[str(msg.id)] = {"categoria": categoria_ticket, "mensagem": mensagem_ticket}
        salvar_paineis(paineis)
        await interaction.followup.send(" ✅ Painel criado!", ephemeral=True)
    except Exception:
        if not interaction.response.is_done():
            await interaction.response.send_message(" Erro no Emoji.", ephemeral=True)
        else:
            await interaction.followup.send(" Erro no Emoji.", ephemeral=True)

@bot.tree.command(name="backup", description="💾 Faz o backup do banco de dados (VIPs e Painéis)")
@app_commands.default_permissions(administrator=True)
async def cmd_backup(interaction: discord.Interaction):
    if os.path.exists(ARQUIVO_VIPS) and os.stat(ARQUIVO_VIPS).st_size > 0:
        await interaction.response.send_message(" 📥 **Backup:**", file=discord.File(ARQUIVO_VIPS), ephemeral=True)
    else: await interaction.response.send_message(" Banco vazio.", ephemeral=True)

@bot.tree.command(name="vips", description="📋 Lista todos os VIPs ativos")
@app_commands.default_permissions(administrator=True)
async def listar_vips(interaction: discord.Interaction):
    vips = carregar_vips()
    if not vips: return await interaction.response.send_message("Nenhum VIP.", ephemeral=True)
    texto = "**📋 Lista VIPs:**\n"
    for chave, data_str in vips.items():
        texto += f"• <@{chave.split('_')[0]}> expira: `{datetime.fromisoformat(data_str).strftime('%d/%m/%Y %H:%M:%S')}`\n"
    await interaction.response.send_message(texto, ephemeral=True)

@bot.tree.command(name="rcon", description="💻 Envia comando ao console")
@app_commands.default_permissions(administrator=True)
async def cmd_rcon(interaction: discord.Interaction, comando: str):
    await interaction.response.defer()
    resposta = await enviar_comando_rcon(comando)
    await interaction.followup.send(f"💻 **Console:**\n```\n{resposta}\n```")

@bot.tree.command(name="fechar_ticket", description="🔒 Encerra o ticket imediatamente")
@app_commands.default_permissions(administrator=True)
async def fechar_ticket(interaction: discord.Interaction):
    if "ticket-" in interaction.channel.name:
        await interaction.response.send_message(" 🔒 **A encerrar em 5s...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()
    else: await interaction.response.send_message(" Usa dentro de um ticket.", ephemeral=True)

@bot.event
async def on_ready():
    global tarefa_monitor_mortes, tarefa_monitor_eventos, tarefa_monitor_call_ingame, tarefa_varredura_fichas, tarefa_retomar_analises
    await bot.change_presence(activity=discord.Game(name="TRABALHANDO..."))
    print(f'✅ Sistema V148 Online e Vigiando!')
    sincronizar_historico_com_personagens_atuais()
    sincronizar_registros_personagens_atuais()

    if not radar_servidor.is_running():
        radar_servidor.start() 
    if not loop_sorteios.is_running():
        loop_sorteios.start()
    if not loop_retentar_registros.is_running():
        loop_retentar_registros.start()
    if not loop_fechar_tickets.is_running():
        loop_fechar_tickets.start()
    if not supervisor_monitores.is_running():
        supervisor_monitores.start()
    if tarefa_monitor_mortes is None or tarefa_monitor_mortes.done():
        tarefa_monitor_mortes = bot.loop.create_task(monitorar_mortes())
    if tarefa_monitor_eventos is None or tarefa_monitor_eventos.done():
        tarefa_monitor_eventos = bot.loop.create_task(monitorar_eventos())
    if tarefa_monitor_call_ingame is None or tarefa_monitor_call_ingame.done():
        tarefa_monitor_call_ingame = bot.loop.create_task(monitorar_call_ingame())
    if tarefa_retomar_analises is None or tarefa_retomar_analises.done():
        tarefa_retomar_analises = bot.loop.create_task(retomar_fichas_em_analise())
    if tarefa_varredura_fichas is None or tarefa_varredura_fichas.done():
        tarefa_varredura_fichas = bot.loop.create_task(varrer_tickets_abertos_fichas())
    with suppress(Exception):
        await descartar_fichas_formato_antigo()

    descartadas = manter_apenas_ficha_mais_recente()
    if descartadas:
        print(f"[FICHAS] {len(descartadas)} ficha(s) duplicada(s) removida(s) na inicializacao.")

    fila_inicial = carregar_fila_registro()
    if fila_inicial:
        print(f"[FICHAS] {len(fila_inicial)} ficha(s) na fila duravel aguardando registro no servidor.")
        if not fila_pendentes_em_espera:
            agendar_processamento_fichas_pendentes()

    vips = carregar_vips()
    hoje = datetime.now()
    remover_imediatamente = []

    for chave, data_str in vips.items():
        try:
            vencimento = datetime.fromisoformat(data_str)
            partes = chave.split('_')
            user_id = int(partes[0])
            cargo_id = int(partes[1])
            canal_id = int(partes[2]) if len(partes) > 2 else None

            guild = next((item for item in bot.guilds if item.get_role(cargo_id)), None)
            if not guild:
                print(f"[VIP] Não encontrei servidor/membro/cargo para o registro {chave}; mantendo-o salvo.")
                continue

            segundos_restantes = (vencimento - hoje).total_seconds()
            if segundos_restantes > 0:
                agendar_remocao_vip_unica(
                    guild.id, user_id, cargo_id, canal_id, segundos_restantes,
                    chave, data_str,
                )
            else:
                remover_imediatamente.append((guild.id, user_id, cargo_id, canal_id, chave))
        except: pass

    for g_id, u_id, c_id, canal_id, chave in remover_imediatamente:
        guild = bot.get_guild(g_id)
        if guild:
            membro = guild.get_member(u_id)
            cargo = guild.get_role(c_id)
            if membro and cargo:
                try: await membro.remove_roles(cargo)
                except: pass
        del vips[chave]
    if remover_imediatamente: salvar_vips(vips)

async def movimento_de_call_foi_feito_por_outra_pessoa(guild, membro_id):
    """Confere o log de auditoria para distinguir arraste de mudanca voluntaria."""
    limite = datetime.now(timezone.utc) - timedelta(seconds=12)
    try:
        async for entrada in guild.audit_logs(limit=8, action=discord.AuditLogAction.member_move):
            alvo = getattr(entrada, "target", None)
            if not alvo or getattr(alvo, "id", None) != membro_id:
                continue
            criado_em = getattr(entrada, "created_at", None)
            if not criado_em or criado_em < limite:
                continue
            executor = getattr(entrada, "user", None)
            if executor and executor.id not in {membro_id, getattr(bot.user, "id", None)}:
                return True
    except (discord.Forbidden, discord.HTTPException) as erro:
        print(f"[CALL PROTEGIDA] Nao consegui ler o registro de auditoria: {erro}")
    return False

async def aguardar_confirmacao_movimento_externo(guild, membro_id, tentativas=4):
    """O audit log pode aparecer alguns segundos depois do evento de voz."""
    for tentativa in range(tentativas):
        if await movimento_de_call_foi_feito_por_outra_pessoa(guild, membro_id):
            return True
        if tentativa + 1 < tentativas:
            await asyncio.sleep(1)
    return False

async def processar_retorno_call_protegida(guild_id, membro_id, canal_origem_id, canal_destino_id):
    """Devolve o usuario protegido somente apos um arraste confirmado."""
    try:
        inicio = time.monotonic()
        guild = bot.get_guild(guild_id)
        membro = guild.get_member(membro_id) if guild else None
        if not guild or not membro:
            return
        if not await aguardar_confirmacao_movimento_externo(guild, membro_id):
            return

        # A espera total e de 5s desde o arraste. O tempo gasto esperando o
        # audit log conta nessa janela, em vez de somar mais cinco segundos.
        espera_restante = max(0, ATRASO_RETORNO_CALL_PROTEGIDA - (time.monotonic() - inicio))
        if espera_restante:
            await asyncio.sleep(espera_restante)
        membro = guild.get_member(membro_id)
        canal_origem = guild.get_channel(canal_origem_id)
        canal_atual = getattr(getattr(membro, "voice", None), "channel", None) if membro else None

        # Se saiu ou mudou de call por vontade propria nesses 5 segundos,
        # nao interferimos. So devolve se ainda estiver no destino do arraste.
        if not membro or not canal_origem or not canal_atual or canal_atual.id != canal_destino_id:
            return

        await membro.move_to(canal_origem, reason="Protecao contra movimentacao de call nao autorizada")
        print(f"[CALL PROTEGIDA] {membro} voltou para {canal_origem.name} apos ser movido por outra pessoa.")
    except (discord.Forbidden, discord.HTTPException) as erro:
        print(f"[CALL PROTEGIDA] Nao consegui devolver o usuario a call: {erro}")
    except asyncio.CancelledError:
        raise
    finally:
        tarefa_atual = asyncio.current_task()
        if tarefas_retorno_call_protegida.get(membro_id) is tarefa_atual:
            tarefas_retorno_call_protegida.pop(membro_id, None)

@bot.event
async def on_voice_state_update(member, before, after):
    """Protege exclusivamente o usuario configurado contra arraste entre calls."""
    if str(member.id) != USUARIO_PROTEGIDO_CALL_ID:
        return
    if before.channel is None or after.channel is None or before.channel.id == after.channel.id:
        return

    tarefa_anterior = tarefas_retorno_call_protegida.pop(member.id, None)
    if tarefa_anterior and not tarefa_anterior.done():
        tarefa_anterior.cancel()

    tarefa = bot.loop.create_task(
        processar_retorno_call_protegida(
            member.guild.id, member.id, before.channel.id, after.channel.id,
        )
    )
    tarefas_retorno_call_protegida[member.id] = tarefa

@bot.event
async def on_message(message):
    if message.author == bot.user: return

    await bot.process_commands(message)

    if categoria_processa_ficha_pos_morte(getattr(message.channel, "category", None)):
        if mensagem_parece_formulario_ficha(message):
            # Formato antigo desativado: so o formulario do botao vale.
            await avisar_ficha_formato_antigo(message.channel, message.author)
            return

    if message.content.startswith('!zomboid'):
        # TRAVA DE CUSTO: a checagem de permissao acontece ANTES de qualquer
        # chamada de API. Jogador comum nunca chega a gastar token do Groq.
        if not usuario_e_staff(message.author):
            with suppress(Exception):
                await message.channel.send(
                    f"🚫 {message.author.mention}, o assistente de IA é de uso exclusivo da staff.",
                    delete_after=10,
                )
            return

        usuario_texto = message.content.replace('!zomboid', '').strip()
        chat_id = message.channel.id

        if usuario_texto.lower() == "esquecer tudo":
            memorias.pop(chat_id, None)
            memorias_ultima_atividade.pop(chat_id, None)
            return await message.channel.send(" 🧠 Memória limpa.")

        user_msg_com_contexto = f"(Ação solicitada por {message.author.mention} ID:{message.author.id}): {usuario_texto}"

        async with message.channel.typing():
            try:
                resposta_groq = await roteador_groq(chat_id, user_msg_com_contexto)
                if "Erro:" in resposta_groq and "Groq" not in resposta_groq:
                    return await message.channel.send(f"⚠ {resposta_groq}")

                encontrou_comando = False

                for linha in resposta_groq.split('\n'):
                    linha_limpa = extrair_linha_comando(linha)
                    if linha_limpa:
                        if not usuario_e_staff(message.author): await message.channel.send("🚫 Acesso Negado."); encontrou_comando = True; break

                        partes_cmd = [d.strip() for d in linha_limpa.replace("CMD:", "").split("|")]
                        dados = partes_cmd + ["", "", "", "", ""]
                        acao, guild = dados[0], message.guild

                        if acao == "ENTRAR_VOZ":
                            try:
                                vc, erro = await conectar_bot_na_call_do_autor(message.author)
                                if erro:
                                    await message.channel.send(erro)
                                else:
                                    await message.channel.send(f"👂 Conectado em {vc.channel.mention}.")
                            except Exception as e:
                                await message.channel.send(f"❌ Não consegui entrar na call: {e}")
                            encontrou_comando = True

                        elif acao == "GRAVAR_VOZ":
                            ok, resposta = await iniciar_gravacao_reuniao(message.author, message.channel)
                            await message.channel.send(resposta)
                            encontrou_comando = True

                        elif acao == "PARAR_VOZ":
                            _, resposta = await encerrar_gravacao_reuniao(guild, message.channel)
                            if resposta not in ("ok", "audio_curto"):
                                await message.channel.send(resposta if isinstance(resposta, str) else "❌ Não consegui encerrar a reunião.")
                            encontrou_comando = True

                        elif acao == "CRIAR_CARGO":
                            if dados[1]:
                                await guild.create_role(name=dados[1], color=pegar_cor(dados[2]))
                                await message.channel.send(f"✅ Cargo **{dados[1]}** criado!")
                            encontrou_comando = True

                        elif acao == "DELETAR_CARGO":
                            cargo = encontrar_cargo(guild, dados[1])
                            if cargo:
                                await cargo.delete()
                                await message.channel.send("🗑 Cargo apagado!")
                            encontrou_comando = True

                        elif acao == "REMOVER_CARGO":
                            nome_cargo = dados[1]
                            id_alvo = "".join(filter(str.isdigit, dados[2]))
                            if id_alvo and nome_cargo:
                                membro = guild.get_member(int(id_alvo))
                                cargo = encontrar_cargo(guild, nome_cargo)
                                if membro and cargo:
                                    await membro.remove_roles(cargo)
                                    await message.channel.send(f"✅ O cargo **{cargo.name}** foi tirado de {membro.mention}!")
                                else: await message.channel.send("  Cargo ou membro não encontrado.")
                            encontrou_comando = True

                        elif acao == "ADD_ROLE":
                            nome_cargo = dados[1]
                            id_alvo = "".join(filter(str.isdigit, dados[2]))
                            if id_alvo and nome_cargo:
                                membro = guild.get_member(int(id_alvo))
                                cargo = encontrar_cargo(guild, nome_cargo)
                                if membro and cargo:
                                    await membro.add_roles(cargo)
                                    await message.channel.send(f"✅ Cargo **{cargo.name}** dado a {membro.mention}!")
                                else: await message.channel.send("  Cargo ou membro não encontrado.")
                            encontrou_comando = True

                        elif acao == "CRIAR_CANAL":
                            nome_canal = dados[1].replace(" ", "-").lower()
                            eh_privado = "sim" in dados[2].lower()
                            if nome_canal:
                                overwrites = None
                                if eh_privado:
                                    overwrites = {
                                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                                        message.author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                                        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                                    }
                                await guild.create_text_channel(nome_canal, overwrites=overwrites)
                                tipo_txt = "🔒 privado" if eh_privado else " público"
                                await message.channel.send(f"✅ Canal {tipo_txt} **{nome_canal}** criado!")
                            encontrou_comando = True

                        elif acao == "ENVIAR_MENSAGEM_CANAL":
                            canal_alvo = encontrar_canal_texto(guild, dados[1])
                            mensagem_cmd = desserializar_texto_cmd("|".join(partes_cmd[2:]))
                            if canal_alvo and mensagem_cmd:
                                await canal_alvo.send(mensagem_cmd)
                                await message.channel.send(f"✅ Mensagem enviada em {canal_alvo.mention}!")
                            else:
                                await message.channel.send("❌ Não encontrei o canal ou a mensagem veio vazia.")
                            encontrou_comando = True

                        elif acao == "EDITAR_MENSAGEM_CANAL":
                            canal_alvo = encontrar_canal_texto(guild, dados[1])
                            mensagem_alvo = await buscar_mensagem_em_canal(canal_alvo, dados[2])
                            novo_texto = desserializar_texto_cmd("|".join(partes_cmd[3:]))
                            if mensagem_alvo and novo_texto:
                                await mensagem_alvo.edit(content=novo_texto)
                                await message.channel.send(f"✅ Mensagem `{mensagem_alvo.id}` editada em {canal_alvo.mention}!")
                            else:
                                await message.channel.send("❌ Não encontrei a mensagem/canal ou o novo texto veio vazio.")
                            encontrou_comando = True

                        elif acao == "APAGAR_MENSAGEM_CANAL":
                            canal_alvo = encontrar_canal_texto(guild, dados[1])
                            mensagem_alvo = await buscar_mensagem_em_canal(canal_alvo, dados[2])
                            if mensagem_alvo:
                                await mensagem_alvo.delete()
                                await message.channel.send(f"✅ Mensagem `{dados[2]}` apagada de {canal_alvo.mention}!")
                            else:
                                await message.channel.send("❌ Não encontrei o canal ou a mensagem informada.")
                            encontrou_comando = True

                        elif acao == "RENOMEAR_CANAL":
                            canal_alvo = encontrar_canal_texto(guild, dados[1])
                            novo_nome = normalizar_nome_canal("|".join(partes_cmd[2:]))
                            if canal_alvo and novo_nome:
                                await canal_alvo.edit(name=novo_nome)
                                await message.channel.send(f"✅ Canal renomeado para **{novo_nome}**!")
                            else:
                                await message.channel.send("❌ Não encontrei o canal ou o novo nome veio vazio.")
                            encontrou_comando = True

                        elif acao == "MOVER_CANAL":
                            canal_alvo = encontrar_canal_texto(guild, dados[1])
                            categoria_alvo = encontrar_categoria(guild, "|".join(partes_cmd[2:]))
                            if canal_alvo and categoria_alvo:
                                await canal_alvo.edit(category=categoria_alvo)
                                await message.channel.send(f"✅ Canal {canal_alvo.mention} movido para **{categoria_alvo.name}**!")
                            else:
                                await message.channel.send("❌ Não encontrei o canal ou a categoria informada.")
                            encontrou_comando = True

                        elif acao == "SALVAR_TEMPLATE":
                            nome_template = dados[1].strip().lower()
                            conteudo_template = desserializar_texto_cmd("|".join(partes_cmd[2:]))
                            if nome_template and conteudo_template:
                                templates = carregar_templates()
                                templates[nome_template] = conteudo_template
                                salvar_templates(templates)
                                await message.channel.send(f"✅ Template **{nome_template}** salvo com sucesso!")
                            else:
                                await message.channel.send("❌ Informe um nome de template e um conteúdo válido.")
                            encontrou_comando = True

                        elif acao == "ENVIAR_TEMPLATE":
                            canal_alvo = encontrar_canal_texto(guild, dados[1])
                            nome_template = dados[2].strip().lower()
                            templates = carregar_templates()
                            conteudo_template = templates.get(nome_template, "")
                            if canal_alvo and conteudo_template:
                                await canal_alvo.send(conteudo_template)
                                await message.channel.send(f"✅ Template **{nome_template}** enviado em {canal_alvo.mention}!")
                            else:
                                await message.channel.send("❌ Não encontrei o canal ou o template informado.")
                            encontrou_comando = True

                        elif acao == "EMOJI_CANAL":
                            canal_alvo = encontrar_canal_texto(guild, dados[1])
                            emoji_canal = dados[2].strip()
                            if canal_alvo and emoji_canal:
                                novo_nome = aplicar_emoji_no_nome_canal(canal_alvo.name, emoji_canal)
                                await canal_alvo.edit(name=novo_nome)
                                await message.channel.send(f"✅ Canal atualizado para **{novo_nome}**!")
                            else:
                                await message.channel.send("❌ Não encontrei o canal ou o emoji não foi informado.")
                            encontrou_comando = True

                        elif acao == "CONSULTAR_REGISTRO_PERSONAGEM":
                            busca_membro = "|".join(partes_cmd[1:]).strip()
                            membro = encontrar_membro_por_busca(guild, busca_membro)
                            if not membro:
                                await message.channel.send("❌ Não encontrei esse jogador no servidor.")
                            else:
                                registros = carregar_registros_personagens()
                                registro = registros.get(str(membro.id))
                                if not registro:
                                    await message.channel.send(f"📭 Não encontrei nenhum registro salvo para {membro.mention}.")
                                else:
                                    embed = montar_embed_registro_personagem(guild, membro, registro)
                                    await message.channel.send(embed=embed)
                            encontrou_comando = True

                        elif acao == "DAR_VIP":
                            nome_vip = dados[1].strip()
                            id_alvo_str = "".join(filter(str.isdigit, dados[2]))
                            try: quantidade = int(dados[3])
                            except: quantidade = 30
                            unidade = dados[4].lower().strip() if dados[4] else "dias"
                            if not id_alvo_str: membro = message.author
                            else:
                                membro = guild.get_member(int(id_alvo_str))
                                if not membro: membro = message.author
                            if membro and nome_vip:
                                cargo_vip = encontrar_cargo(guild, nome_vip)
                                if not cargo_vip:
                                    nome_novo = nome_vip
                                    if nome_novo.startswith("<@&"): nome_novo = "Novo Cargo VIP"
                                    cargo_vip = await guild.create_role(name=nome_novo, color=discord.Color.gold())
                                try:
                                    await conceder_vip_temporario(
                                        guild, membro, cargo_vip, quantidade, unidade, message.channel.id,
                                        f"VIP concedido por {message.author} via !zomboid",
                                    )
                                    await message.channel.send(f"💎 O cargo **{cargo_vip.name}** foi entregue a {membro.mention} por {quantidade} {unidade}! O relógio está a contar.")
                                except discord.Forbidden: await message.channel.send(f" **ERRO:** Discord me bloqueou de dar o cargo **{cargo_vip.name}**. Arraste meu cargo pra cima dele nas configs.")
                            else: await message.channel.send(" Falha crítica ao encontrar o membro ou o cargo.")
                            encontrou_comando = True
                            
                        elif acao == "REMOVER_REGISTRO_VIP":
                            id_alvo_str = "".join(filter(str.isdigit, dados[1]))
                            if id_alvo_str:
                                vips = carregar_vips()
                                chaves_para_remover = [k for k in vips.keys() if k.startswith(f"{id_alvo_str}_")]
                                if chaves_para_remover:
                                    membro = guild.get_member(int(id_alvo_str))
                                    for k in chaves_para_remover:
                                        partes = k.split('_')
                                        cargo_id = int(partes[1])
                                        cargo = guild.get_role(cargo_id)
                                        if membro and cargo:
                                            try: await membro.remove_roles(cargo)
                                            except: pass
                                        del vips[k]
                                    salvar_vips(vips)
                                    await message.channel.send(f"✅ O jogador <@{id_alvo_str}> foi removido do registro VIP e seus cargos foram retirados.")
                                else: await message.channel.send(" Esse jogador não consta no registro de VIPs ativos.")
                            encontrou_comando = True

                        elif acao == "MODIFICAR_VIP":
                            sub_acao = dados[1].lower().strip()
                            id_alvo_str = "".join(filter(str.isdigit, dados[2]))
                            try: quantidade = int(dados[3])
                            except: quantidade = 0
                            unidade = dados[4].lower().strip() if dados[4] else "dias"

                            if id_alvo_str and quantidade > 0:
                                vips = carregar_vips()
                                chaves_user = [k for k in vips.keys() if k.startswith(f"{id_alvo_str}_")]
                                if chaves_user:
                                    for k in chaves_user:
                                        vencimento_atual = datetime.fromisoformat(vips[k])
                                        delta = timedelta(minutes=quantidade) if "minuto" in unidade else timedelta(days=quantidade)
                                        
                                        if sub_acao == "adicionar": novo_vencimento = vencimento_atual + delta
                                        elif sub_acao == "diminuir": novo_vencimento = vencimento_atual - delta
                                        else: novo_vencimento = vencimento_atual
                                            
                                        vips[k] = novo_vencimento.isoformat()
                                    salvar_vips(vips)
                                    acao_txt = "adicionado(s)" if sub_acao == "adicionar" else "subtraído(s)"
                                    await message.channel.send(f" O tempo VIP de <@{id_alvo_str}> foi modificado: **{quantidade} {unidade}** {acao_txt} no registro!\n*(Dica: O banco foi atualizado. Para cravar o novo horário de remoção perfeito, basta usar o `/deploy` ou reiniciar o bot quando puder).*")
                                else: await message.channel.send(" Esse jogador não tem nenhum VIP ativo para modificar.")
                            else: await message.channel.send(" Faltou informar a quantidade correta ou o jogador.")
                            encontrou_comando = True

                        elif acao == "LIMPAR_TODOS_VIPS":
                            vips = carregar_vips()
                            if not vips:
                                await message.channel.send(" O registro de VIPs já está vazio.")
                            else:
                                for k in list(vips.keys()):
                                    partes = k.split('_')
                                    if len(partes) >= 2:
                                        user_id = int(partes[0])
                                        cargo_id = int(partes[1])
                                        membro = guild.get_member(user_id)
                                        cargo = guild.get_role(cargo_id)
                                        if membro and cargo:
                                            try: await membro.remove_roles(cargo)
                                            except: pass
                                salvar_vips({}) 
                                await message.channel.send("🧹 **Registro de VIPs completamente limpo!** Todos os tempos foram zerados e os cargos (que consegui achar) foram retirados.")
                            encontrou_comando = True

                        elif acao == "FECHAR_CANAIS":
                            canais_alvo = dados[1].split(",")
                            fechados = []
                            for c_nome in canais_alvo:
                                c_nome = c_nome.strip()
                                canal = None
                                if c_nome.startswith("<#") and c_nome.endswith(">"):
                                    id_canal = int("".join(filter(str.isdigit, c_nome)))
                                    canal = guild.get_channel(id_canal)
                                else:
                                    canal = discord.utils.get(guild.text_channels, name=c_nome.lower().replace(" ", "-"))

                                if canal:
                                    await canal.delete()
                                    fechados.append(canal.name)
                            if fechados: await message.channel.send(f"🗑 Fechei os canais: {', '.join(fechados)}")
                            else: await message.channel.send(" Não encontrei os canais que você pediu.")
                            encontrou_comando = True

                        elif acao == "FECHAR_CATEGORIA":
                            cat_nome = dados[1].strip()
                            categoria = discord.utils.get(guild.categories, name=cat_nome)
                            if categoria:
                                fechados = 0
                                for c in categoria.text_channels:
                                    if "ticket-" in c.name:
                                        await c.delete()
                                        fechados += 1
                                await message.channel.send(f"🗑 Fechei {fechados} tickets da categoria **{categoria.name}**.")
                            else: await message.channel.send(f"  Não encontrei nenhuma categoria chamada '{cat_nome}'.")
                            encontrou_comando = True
                        break

                if not encontrou_comando:
                    msg_limpa = resposta_groq.replace("CMD:", "").strip()
                    if len(msg_limpa) <= 2000: await message.channel.send(msg_limpa)
                    else:
                        for i in range(0, len(msg_limpa), 1900): await message.channel.send(msg_limpa[i:i+1900]); await asyncio.sleep(0.5)

            except Exception as e:
                await message.channel.send(f"⚠ Erro no servidor central: {e}")

@bot.tree.command(name="diagnostico_call_ingame", description="Mostra se o monitor de call esta lendo jogadores e calls corretamente")
@app_commands.default_permissions(administrator=True)
async def diagnostico_call_ingame(interaction: discord.Interaction):
    """Diagnostico sem kick para confirmar a integracao na host."""
    if await bloquear_se_nao_for_staff(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    caminho_ativo = await asyncio.to_thread(caminho_players_online_ativo)
    caminhos_encontrados = await asyncio.to_thread(caminhos_players_online_friendhost)
    jogadores_online = await ler_jogadores_online_monitoramento()

    embed = discord.Embed(title="Diagnostico da Call Obrigatoria", color=discord.Color.blurple())
    embed.add_field(name="Calls que contam", value="`" + "`, `".join(sorted(nomes_calls_permitidas())) + "`", inline=False)
    embed.add_field(name="Tolerancia antes do kick", value=f"**{TEMPO_GRACA_CALL_INGAME} segundos**", inline=True)

    calls_ativas = []
    ids_nas_calls = ids_na_call_ingame()
    for guild in bot.guilds:
        for canal in list(guild.voice_channels) + list(guild.stage_channels):
            if canal_e_call_ingame(canal):
                calls_ativas.append(f"{canal.name}: {len(canal.members)} membro(s)")
    embed.add_field(
        name="Pessoas nas calls permitidas",
        value=f"**{len(ids_nas_calls)}**\n" + ("\n".join(calls_ativas[:8]) or "Nenhuma call permitida encontrada."),
        inline=False,
    )

    if not caminho_ativo:
        if jogadores_online:
            embed.color = discord.Color.green()
            vinculados_rcon = [
                f"{dados.get('username_jogo') or '?'} -> {dados.get('personagem') or '?'}"
                for dados in jogadores_online.values()
            ]
            embed.add_field(
                name="Lista online via RCON",
                value=(
                    "O TXT do mod nao esta montado para o bot, mas o RCON respondeu e sera usado como fallback.\n"
                    f"**{len(vinculados_rcon)}** jogador(es) vinculados; mostrando os primeiros 12.\n"
                    "```" + "\n".join(vinculados_rcon[:12]) + "```"
                )[:1000],
                inline=False,
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        embed.color = discord.Color.red()
        encontrados = "\n".join(caminhos_encontrados[:5]) or "nenhum"
        embed.add_field(
            name="Arquivo online indisponivel ou antigo",
            value=("O bot nao pode aplicar kick sem uma lista atual de jogadores.\n"
                   f"Procurado: `{CAMINHO_PLAYERS_ONLINE}`\n"
                   f"Encontrados: ```{encontrados}```")[:1000],
            inline=False,
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    try:
        idade = max(0, int(time.time() - os.path.getmtime(caminho_ativo)))
        with open(caminho_ativo, "r", encoding="utf-8", errors="replace") as arquivo:
            usernames = [linha.strip() for linha in arquivo if linha.strip()]
    except Exception as erro:
        embed.color = discord.Color.red()
        embed.add_field(name="Falha ao ler arquivo", value=f"`{erro}`", inline=False)
        return await interaction.followup.send(embed=embed, ephemeral=True)

    embed.add_field(
        name="Arquivo de jogadores online",
        value=f"`{caminho_ativo}`\nAtualizado ha **{idade}s** · {len(usernames)} username(s)",
        inline=False,
    )
    embed.add_field(name="Usernames exportados pelo mod", value="```" + ("\n".join(usernames[:12]) or "(ninguem online)") + "```", inline=False)
    vinculados = [f"{dados.get('username_jogo') or '?'} -> {dados.get('personagem') or '?'}" for dados in jogadores_online.values()]
    embed.add_field(
        name="Jogadores que o bot conseguiu vincular ao Discord",
        value=("```" + ("\n".join(vinculados[:12]) or "(nenhum)") + "```")[:1000],
        inline=False,
    )
    if usernames and not jogadores_online:
        embed.color = discord.Color.red()
        embed.add_field(
            name="Atencao: nenhum jogador foi vinculado",
            value=("O arquivo existe, mas o bot nao conseguiu associar os usernames aos registros. "
                   "Confira se `personagens.json` esta preservado e se os usernames do arquivo sao os mesmos logins criados pelo bot."),
            inline=False,
        )
    elif jogadores_online:
        embed.color = discord.Color.green()

    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="diagnostico_protecao_call", description="Verifica a protecao contra arraste de call do Thiago")
@app_commands.default_permissions(administrator=True)
async def diagnostico_protecao_call(interaction: discord.Interaction):
    """Mostra as permissoes e o ultimo arraste que o Discord registrou."""
    if await bloquear_se_nao_for_staff(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if not guild or not bot.user:
        return await interaction.followup.send("Este comando so funciona dentro de um servidor.", ephemeral=True)

    membro_bot = guild.get_member(bot.user.id)
    permissoes = getattr(membro_bot, "guild_permissions", None)
    pode_ler_auditoria = bool(getattr(permissoes, "view_audit_log", False))
    pode_mover = bool(getattr(permissoes, "move_members", False))
    alvo_id = int(USUARIO_PROTEGIDO_CALL_ID) if USUARIO_PROTEGIDO_CALL_ID.isdigit() else None
    alvo = guild.get_member(alvo_id) if alvo_id else None
    call_atual = getattr(getattr(alvo, "voice", None), "channel", None)

    embed = discord.Embed(title="Diagnostico da Protecao contra Arraste", color=discord.Color.green())
    embed.add_field(
        name="Usuario protegido",
        value=(f"<@{USUARIO_PROTEGIDO_CALL_ID}> (`{USUARIO_PROTEGIDO_CALL_ID}`)"
               if alvo_id else "ID configurado invalido"),
        inline=False,
    )
    embed.add_field(
        name="Permissoes do bot",
        value=(f"Ver registro de auditoria: {'✅' if pode_ler_auditoria else '❌'}\n"
               f"Mover membros: {'✅' if pode_mover else '❌'}"),
        inline=True,
    )
    embed.add_field(
        name="Call atual",
        value=call_atual.mention if call_atual else "O usuario nao esta em call (ou nao esta no cache do servidor).",
        inline=True,
    )

    if not pode_ler_auditoria or not pode_mover:
        embed.color = discord.Color.red()
        embed.add_field(
            name="Acao necessaria",
            value="Dê ao cargo do bot as permissoes **Ver registro de auditoria** e **Mover membros**. "
                  "Sem o registro, o Discord nao permite diferenciar um arraste de uma troca voluntaria.",
            inline=False,
        )

    ultimo_arraste = None
    erro_auditoria = None
    try:
        async for entrada in guild.audit_logs(limit=12, action=discord.AuditLogAction.member_move):
            if alvo_id and getattr(getattr(entrada, "target", None), "id", None) == alvo_id:
                ultimo_arraste = entrada
                break
    except (discord.Forbidden, discord.HTTPException) as erro:
        erro_auditoria = str(erro)

    if ultimo_arraste:
        executor = getattr(ultimo_arraste, "user", None)
        criado_em = getattr(ultimo_arraste, "created_at", None)
        quando = discord.utils.format_dt(criado_em, style="R") if criado_em else "horario indisponivel"
        embed.add_field(
            name="Ultimo arraste registrado",
            value=f"Por {getattr(executor, 'mention', str(executor or 'desconhecido'))} · {quando}",
            inline=False,
        )
    elif erro_auditoria:
        embed.color = discord.Color.red()
        embed.add_field(name="Registro de auditoria", value=f"Falha ao consultar: `{erro_auditoria[:700]}`", inline=False)
    else:
        embed.add_field(
            name="Registro de auditoria",
            value="Nenhum arraste recente desse usuario foi encontrado. Faca um teste: outra pessoa move voce entre duas calls.",
            inline=False,
        )

    await interaction.followup.send(embed=embed, ephemeral=True)

bot.run(DISCORD_TOKEN)
