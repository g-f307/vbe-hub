# Validação da issue #92

Validação técnica realizada em 20/11/2026 com dados demonstrativos locais, sem chamadas novas à IA.
Não representa validação clínica ou epidemiológica. A OpenAI permanece no processamento assíncrono;
o modal somente consulta as sugestões persistidas.

## Resultado automatizado

- Backend: 279 testes unitários e 64 de integração aprovados.
- Frontend: 61 testes aprovados; ESLint e build de produção aprovados.
- Ruff, auditoria estrita da documentação e `git diff --check` aprovados.
- Integração executada em um projeto Compose isolado (`vbe-hub-92-test`), sem usar o banco principal.

Os testes cobrem projeção e origem dos campos, datas sem hora, ausência de metadados,
timestamps simulados, complementação e conflitos, compatibilidade, duas abas, contador elegível,
paginação de candidatos, consulta somente leitura e retorno com cursor/filtros/visualização.
Falhas do serviço e conflitos de versão têm cobertura automatizada dos adaptadores de ação.

## Percurso verificado no navegador

1. Acesso ao detalhe com retorno à segunda página da fila em lista e `state=all`.
2. Abertura de Sinais relacionados e modal com três candidatos disponíveis.
3. Seleção de dois candidatos e expansão da justificativa por Ler mais.
4. Confirmação: modal fechado, dois incorporados visíveis e contador reduzido de 3 para 1,
   sem atualização manual da página.
5. Consulta de incorporado somente para leitura, com trilha fila → principal → incorporado.
6. Retorno à aba Sinais relacionados preservando o endereço da fila com cursor e visualização.
7. Fechamento por Escape sem composição, foco devolvido ao botão, foco contido no modal e
   rolagem em viewport de 390 × 844, sem transbordamento horizontal da página.
8. Remoção auditável dos dois vínculos criados no teste, sem apagar qualquer fonte.

O teste humano deixou a cabeça em triagem e preservou seu histórico de composição/correção,
como determina o workflow. Não foram removidos vínculos anteriores nem reinicializado o banco.
Os volumes do projeto isolado de testes foram descartados após a validação.

## Capturas

As capturas mostram conteúdo demonstrativo, sem credenciais ou informações pessoais.
Algumas foram feitas durante a composição de validação, antes de desfazer os vínculos.
Na revisão posterior, os textos e ícones da navbar passaram a branco. A faixa azul de contraste
foi retirada por orientação visual: o fundo final permanece no azul principal `#319AD3`.
As capturas anteriores preservam o registro das revisões, não uma certificação de contraste.

- [Informações — desktop](informacoes-desktop.png)
- [Informações — móvel](informacoes-mobile.png)
- [Modal — desktop](modal-desktop.png)
- [Modal — móvel](modal-mobile.png)
- [Sinais relacionados — desktop](relacionados-desktop.png)
- [Consulta de incorporado — desktop](incorporado-desktop.png)
- [Navbar branca — revisão desktop](navbar-desktop.png)

## Reproduzir

```bash
docker compose up --build --detach --wait
docker compose --profile tools run --build --rm --no-deps unit-test
docker compose --profile tools run --build --rm frontend-test
docker compose --profile tools run --rm frontend-lint
docker compose --profile tools run --build --rm lint
docker compose --profile tools run --rm docs-check
```

Os testes de integração devem usar infraestrutura descartável, não o banco da demonstração.
O painel fica em `http://localhost:3000`. Não é necessário reprocessar dados com IA para
atualizar cores, abas ou os campos apresentados. Metadados inexistentes aparecem como
“Não informado”; a interface não preenche valores copiando o exemplo do orientador.

## Adequação dos exemplos aos campos operacionais

Ainda em 20/11/2026, foi executado `demo-refresh-information` sobre a demonstração local:
40 origens identificadas, 40 atualizadas e zero atualizações na repetição. O comando apenas
completa metadados demonstrativos ausentes. Novas cargas incluem os mesmos dados declarados,
sem apresentá-los como extração ou decisão da IA; os limites estão no
[guia de execução](../../development.md#atualizar-metadados-dos-exemplos-existentes).

Uma comparação transacional de todas as tabelas públicas antes/depois, excluindo somente o
envelope `signal_information`, confirmou igualdade dos demais dados: 40 sinais, 40 descrições,
40 extrações, 40 embeddings, 56 avaliações/sugestões de relações, seis fichas, 13 registros de
participação e 15 eventos de composição preservados. Não houve enfileiramento nem chamada à IA.
A API local retornou os novos campos no detalhe do sinal de mídia sobre o Zumbi.

Nesta revisão, 279 testes unitários e 65 de integração passaram, assim como Ruff, `docs-check`
e `git diff --check`. A auditoria adicional com a versão atual do skill r-doc apontou dez erros
estruturais e um aviso preexistentes (IDs documentais duplicados, navegação de evidências,
sucessores de documentos substituídos e revisão vencida do plano). Portanto, essa auditoria
ampliada não está aprovada; a verificação documental oficial do repositório está aprovada.
