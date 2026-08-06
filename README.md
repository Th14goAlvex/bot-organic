# Bot Organic RP — Project Zomboid

Bot de Discord que administra o servidor de Project Zomboid do **Organic RP**:
registro de personagens via ficha, sistema anti-fraude pós-morte, integração RCON,
controle de VIPs, sorteios e monitoramento do servidor.

## Principais recursos

- **Registro de personagem por formulário** — botão que abre um Modal no Discord
  com campos separados (Nome, Senha, Profissão, História). Ficha digitada no chat
  também continua funcionando.
- **Fila durável de registro** — as fichas ficam gravadas em disco até o
  personagem estar confirmado no servidor. Nada se perde se o bot reiniciar,
  se o servidor estiver fechado ou se o RCON falhar.
- **Anti-fraude pós-morte** — só libera personagem novo se o anterior constar
  como morto no banco do jogo ou nos logs.
- **Monitores** — mortes, eventos e call obrigatória in-game, com supervisor que
  reinicia qualquer monitor que caia.
- **VIPs com expiração automática**, sorteios e painéis de ticket.
- **Assistente de IA** (Groq) e ata de reunião por áudio (Gemini), restritos à staff.

## Requisitos

- Python 3.12+
- Um servidor de Project Zomboid com RCON habilitado
- Chaves de API: Discord, Groq e Gemini

## Instalação

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha com as credenciais do servidor
(elas não ficam no repositório — peça ao administrador):

```bash
copy .env.example .env      # Windows
cp .env.example .env        # Linux
```

Depois é só rodar:

```bash
python bot.py
```

## Comandos de staff

| Comando | O que faz |
|---|---|
| `/fila_registros` | Mostra as fichas na fila esperando o servidor abrir |
| `/aprovar_ficha` | Força a aprovação da ficha do ticket, ignorando o anti-fraude |
| `/historico_registro` | Consulta o último registro de personagem de um jogador |
| `/enviar_formulario` | Posta o botão do formulário de ficha no canal |
| `/iniciar_reuniao` · `/encerrar_reuniao` | Grava a call e gera a ata |
| `!deploy` | Sincroniza os slash commands |

## Dados e privacidade

Os bancos em JSON (`registros_personagens.json`, `personagens.json`,
`historico_personagens.json`, etc.) contêm **dados pessoais de jogadores reais**
— incluindo IDs do Discord e senhas de acesso ao servidor. Eles estão no
`.gitignore` e **não devem ser versionados nem publicados**.

Toda gravação desses arquivos é atômica (`.tmp` → `fsync` → `os.replace`), com
backup `.bak` automático e recuperação em caso de arquivo corrompido.

## Estrutura

```
bot.py               Todo o bot
requirements.txt     Dependências
.env.example         Modelo de configuração
*.json               Bancos de dados locais (não versionados)
```
