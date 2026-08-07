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
| `/agendar_abertura` | Marca a data/hora em que a aprovação de personagens começa |
| `/bot_atualizar` | Baixa a última versão deste repositório e reinicia o bot |
| `/versao_bot` | Mostra a versão instalada e se há atualização |
| `/diagnostico_mortes` | Mostra qual arquivo de mortes o bot lê e como interpreta |
| `/configurar_vidas` · `/adicionar_vidas` · `/ver_vidas` | Sistema de vidas por temporada |
| `/fila_registros` | Mostra as fichas na fila esperando o servidor abrir |
| `/aprovar_ficha` | Força a aprovação da ficha do ticket, ignorando o anti-fraude |
| `/historico_registro` | Consulta o último registro de personagem de um jogador |
| `/enviar_formulario` | Posta o botão do formulário de ficha no canal |
| `/iniciar_reuniao` · `/encerrar_reuniao` | Grava a call e gera a ata |
| `!deploy` | Sincroniza os slash commands |

## Atualização remota

Depois de fazer deploy na host, novas versões são aplicadas pelo próprio Discord
com `/bot_atualizar` — não é preciso acesso ao servidor.

O comando baixa a última versão deste repositório, **valida que o código compila
antes de gravar qualquer coisa**, guarda um backup do que foi substituído em
`backup_update/` e só então reinicia o processo. Se o download falhar, o código
vier quebrado ou a instalação de dependências der erro, ele restaura o backup e
o bot continua na versão anterior.

O updater troca **apenas arquivos `.py` e o `requirements.txt`**. Nenhum `.json`
e nenhum `.env` é tocado — mesmo os que existem neste repositório, como o
`paineis.json`.

Todo o estado em andamento sobrevive ao reinício: fichas na fila, análises de
personagem em curso, VIPs com vencimento marcado e sorteios ativos são retomados
automaticamente quando o bot volta.

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
