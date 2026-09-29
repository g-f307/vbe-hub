# VBE Hub

Prova de conceito para integrar, correlacionar e apresentar sinais de alerta em saúde pública provenientes de mídia e vigilância comunitária. A solução apoia a triagem humana; não confirma surtos nem toma decisões sanitárias.

Nesta etapa, o projeto usa dados sintéticos em formatos inspirados nas fontes EIOS e Guardiões da Saúde. Conectores reais não fazem parte da validação inicial.

## Objetivo da validação

Até o fim de outubro/início de novembro de 2026, demonstrar que registros heterogêneos podem ser normalizados, correlacionados e consolidados em sinais de alerta revisáveis por um analista.

## Documentação

Comece por [docs/README.md](docs/README.md). As decisões importantes estão em [docs/decisions/README.md](docs/decisions/README.md).

## Estado atual

Planejamento e documentação inicial. Ainda não há código executável, integração com APIs reais ou credenciais configuradas.

## Reprodutibilidade planejada

Docker Compose será a interface oficial de execução e validação da PoC. Ao concluir a primeira etapa, um dispositivo com Git, Docker e Docker Compose deverá conseguir preparar o ambiente a partir do repositório, sem instalar diretamente Python, Node.js, PostgreSQL ou Redis.

O contrato de inicialização pretendido é:

```bash
git clone https://github.com/g-f307/vbe-hub.git
cd vbe-hub
cp .env.example .env
docker compose up --build
```

Esses comandos ainda não estão implementados. A Issue #1 é responsável por torná-los executáveis e documentar qualquer comando adicional estritamente necessário, como migrations e carga do cenário sintético.
