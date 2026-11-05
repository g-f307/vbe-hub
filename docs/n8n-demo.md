---
id: DEMO-001
type: guide
status: active
title: Demonstração do fluxo de fontes dispersas com n8n
created: 2026-11-04
updated: 2026-11-04
owner: VBE Hub
related_docs:
  - ADR-004
  - ADR-009
  - API-007
---

# Demonstração do fluxo de fontes dispersas com n8n

Esta demonstração torna visível a problemática central da PoC: uma notícia e um relato comunitário
chegam por caminhos distintos, são processados pelo backend e podem originar um card consolidado
para revisão. Todos os textos são sintéticos. O resultado automático é uma sugestão auditável, não
uma confirmação de evento de saúde.

## O que o fluxo demonstra

O workflow `VBE Hub — fontes dispersas e consolidação` contém duas entradas identificáveis:

- **Fonte 1 — notícia:** simula um registro de mídia;
- **Fonte 2 — relato comunitário:** simula um registro comunitário independente.

O n8n reúne as duas entradas e solicita ao backend a execução de um dos três cenários fechados:

| Cenário | Relação demonstrada | Resultado esperado |
| --- | --- | --- |
| `related` | Evidências corroborantes | Um card consolidado com as duas origens. |
| `incompatible` | Evidências incompatíveis | Dois cards separados. |
| `ambiguous` | Contexto relacionado, mas inconclusivo | Dois cards ligados por contexto para revisão profissional. |

O n8n apenas apresenta e orquestra a demonstração. Persistência, normalização, ficha técnica,
relação, consolidação e prioridade continuam sob responsabilidade do backend canônico.

## Rodada limpa: estado antes e depois

Use sempre o projeto isolado `vbe-hub-demo`. O primeiro comando remove **somente** os containers,
rede e volumes desse projeto demonstrativo; ele não remove o banco do projeto Compose padrão.

```bash
docker compose -p vbe-hub-demo --profile demo down --volumes
docker compose -p vbe-hub-demo --profile demo up --build --detach --wait
```

Abra o painel em `http://localhost:3000/triagem`. Antes da execução, a fila deve mostrar o estado
vazio. A resposta canônica também pode ser verificada em `http://localhost:8000/signals`.

Abra `http://localhost:5678`, crie a conta proprietária **local** solicitada pelo n8n e selecione o
workflow importado. No nó **Configuração da demonstração**, mantenha inicialmente:

- `scenario`: `related`;
- `mode`: `offline`.

Execute o workflow. O último nó resume a relação sugerida, os itens criados e os identificadores dos
cards. Recarregue `/triagem`: o estado posterior deve conter um card com evidências de mídia e
comunidade. A investigação do card preserva o vínculo com os dois registros de origem. Reexecutar o
mesmo cenário é idempotente e não duplica o card.

Para repetir a comparação desde o banco vazio, execute novamente os dois comandos de reset e subida.

## Modo online opcional

O modo `offline` usa fichas sintéticas congeladas e não consome API externa. Para demonstrar a
extração com OpenAI, configure `OPENAI_API_KEY` apenas no `.env` local e troque `mode` para
`online`. Uma primeira execução faz no máximo duas extrações — uma por fonte — e o cache persistido
evita nova cobrança para entradas idênticas.

No modo online, a IA estrutura as duas fontes. A relação usada pelos três cenários é deliberadamente
pré-definida para que a apresentação seja repetível; portanto, esta demonstração não mede acurácia
do modelo e não substitui os protocolos de avaliação do projeto.

## Segurança e limites

- o workflow não contém chave de API; somente o backend recebe a credencial pelo ambiente;
- cenário e modo são listas fechadas, não texto arbitrário enviado a ferramentas;
- o n8n não recebe acesso ao banco e chama apenas a rota interna da API;
- diagnósticos, catálogo de templates e notificações externas do n8n ficam desativados;
- os dados são sintéticos e não devem ser substituídos por relatos identificáveis;
- a conta local do n8n é apenas para demonstração e não representa autenticação institucional.

Para encerrar sem apagar a evidência local, use:

```bash
docker compose -p vbe-hub-demo --profile demo down
```
