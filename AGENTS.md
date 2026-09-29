# VBE Hub: contexto do projeto

O VBE Hub é uma prova de conceito de Vigilância Baseada em Eventos (VBE) para correlacionar sinais de mídia e de comunidade. A decisão sanitária final pertence sempre ao profissional de vigilância.

## Leitura inicial

1. [README.md](README.md)
2. [docs/README.md](docs/README.md)
3. Documento pertinente à tarefa em `docs/`
4. Decisões em [docs/decisions/README.md](docs/decisions/README.md), quando a tarefa afetar arquitetura ou dados

## Diretórios previstos

- `docs/`: requisitos, arquitetura, contrato dos dados sintéticos e decisões.
- `backend/`: API e processamento assíncrono (a criar).
- `frontend/`: painel web (a criar).
- `infra/`: execução local e banco de dados (a criar).

## Regras obrigatórias

- Não incluir chaves de API, dados pessoais ou relatos individualmente identificáveis no repositório.
- Tratar resultados de IA como sugestão auditável, nunca como confirmação de evento ou prioridade definitiva.
- Preservar o vínculo entre todo sinal consolidado e seus registros de origem.
- Tratar Docker Compose como interface oficial de execução, teste e demonstração da PoC; a validação em outro dispositivo não pode depender de Python, Node.js, PostgreSQL ou Redis instalados no host.
- Atualizar a documentação afetada ao mudar o contrato de dados ou uma decisão arquitetural.
