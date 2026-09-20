# Arquitetura, Pontos Fracos e Débitos Técnicos (SGE)

Este documento centraliza a análise crítica da arquitetura atual do Sistema de Gestão de Estoque (SGE), destacando seus pontos fracos, limitações de negócio e débitos técnicos conhecidos até a versão 1.6.5.

## 1. Limitações de Arquitetura e Infraestrutura

### 1.1. Banco de Dados (SQLite)
- **Ponto Fraco:** O sistema utiliza `SQLite` como banco de dados padrão de produção (`data/db.sqlite3`).
- **Impacto:** Embora o Django ofereça suporte e o sistema utilize `transaction.atomic()` e `select_for_update()` para evitar condições de corrida em dados críticos, o SQLite possui limitações severas de concorrência para escrita. Em um cenário de múltiplos operadores registrando movimentações simultaneamente, podem ocorrer locks no banco inteiro (`database is locked`).
- **Recomendação:** Planejar a migração para **PostgreSQL** caso o volume de operações simultâneas ou a base de usuários cresça significativamente.

### 1.2. Leitor de Código de Barras (Web/Câmera)
- **Ponto Fraco:** O leitor de código de barras implementado no frontend (`html5-qrcode`) utiliza a câmera do dispositivo via navegador.
- **Impacto:** A precisão e a velocidade de leitura dependem fortemente da qualidade da câmera do usuário, das condições de iluminação e do foco de perto do celular/computador. Leitores a laser (USB/Bluetooth físicos) são ordens de grandeza mais rápidos em um ambiente de almoxarifado.
- **Recomendação:** Garantir que o sistema suporte e seja testado com a entrada de dados via teclado (para leitores físicos emulação de teclado), tratando a câmera web como fallback ou para uso estritamente móvel.

## 2. Limitações de Negócio e Domínio

### 2.1. Rastreabilidade de Lotes e Embalagens Físicas (Rolos/Vidros)
- **Ponto Fraco:** O modelo de dados trata itens como "Rolos" e "Vidros" apenas como **exibições calculadas** (`quantidade_rolos_estimada`) a partir do saldo base total.
- **Impacto:** O sistema sabe que existem "100 metros de tecido", mas não tem como diferenciar se isso está dividido em 2 rolos de 50m ou 10 rolos de 10m. Isso impede a rastreabilidade estrita (ex: "Rolo #005 acabou" ou controle de data de validade por lote de tinta).
- **Recomendação:** Se a operação exigir maior precisão, será necessário criar uma entidade filha (ex: `Lote` ou `EmbalagemFisica`) vinculada ao `Produto`.

### 2.2. Importação/Exportação Básica
- **Ponto Fraco:** Scripts como `importar_estoque.py` são ferramentas operacionais separadas.
- **Impacto:** O usuário comum depende de intervenção técnica para realizar manutenções em massa na base.
- **Recomendação:** Construir rotas no frontend para upload/download de CSV/XLSX lidando graciosamente com falhas de formato.

## 3. Débitos Técnicos (Technical Debt)

### 3.1. Código Legado (App `omie`)
- **Ponto Fraco:** Existe um app Django chamado `omie` no código, mantido exclusivamente para o histórico de migrations e remoção de tabelas antigas.
- **Impacto:** Mantém código "morto" na codebase, poluindo a estrutura e exigindo cuidado para que novas regras não sejam inseridas ali.
- **Recomendação:** Finalizar o ciclo de descontinuação (squash migrations) e remover o app `omie` do projeto em uma refatoração futura.

### 3.2. Ausência de Testes Automatizados no Frontend
- **Ponto Fraco:** O backend possui uma suíte robusta, mas o frontend (React) carece de testes automatizados sistemáticos.
- **Impacto:** Mudanças críticas (como atualizar bibliotecas ou refatorar lógica de hooks do TanStack Query) dependem de teste manual. Não há barreira de CI impedindo a quebra de um formulário.
- **Recomendação:** Implementar `Vitest` para lógica (hooks e utils) e `Playwright` para os fluxos essenciais de UI (ex: Modal de Entrada/Saída de estoque).

## 4. Segurança e Auditoria

### 4.1. Deleção Física vs Deleção Lógica (Soft Delete)
- **Ponto Fraco:** A exclusão da maioria dos registros (Fornecedores, Produtos) aplica um *hard delete* (apaga do banco).
- **Impacto:** A perda acidental de um `Produto` pode inviabilizar relatórios passados ou corromper referências, exigindo complexidade para manter a auditoria em `LogAcao` (e os Fechamentos já usam *snapshot* justamente por causa disso).
- **Recomendação:** Implementar `Soft Delete` (ex: `ativo = False`) para as entidades de domínio, preservando a integridade referencial ao longo do tempo.