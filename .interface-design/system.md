# SGE Interface Design System

## Direção

O SGE é uma ferramenta operacional para equipes de estoque. A interface deve
ser calma, objetiva e rápida de ler em um almoxarifado, com foco em localizar
produtos, entender alertas e registrar entradas ou saídas.

Metáforas do domínio: etiquetas, caixas, prateleiras, sinalização de alerta,
inventário e fechamento contábil.

Assinatura do produto: a ação central da navegação inferior é uma FAB de
movimentação rápida. Ela representa o gesto operacional mais frequente e deve
continuar sendo o principal atalho no mobile.

Evitar padrões genéricos: filtros comprimidos em uma linha, tabelas sem
contexto em telas estreitas e grupos de ações sem uma ação primária clara.

## Tokens e profundidade

- Fundo em slate claro (`--sge-bg`) e superfícies brancas (`--sge-surface`),
  com `--sge-surface-subtle` para áreas de apoio e cabeçalhos.
- Azul (`--sge-primary`) é reservado para identidade, foco e ação primária.
- Verde, âmbar e vermelho comunicam estado operacional; não usar como
  decoração.
- Profundidade baseada em bordas suaves e sombras discretas (`--sge-shadow-sm`
  e `--sge-shadow-md`). Não misturar com sombras dramáticas.
- Raios existentes: pequeno para controles, médio para ícones e grande para
  cards e painéis.
- Espaçamento deve usar os tokens `--sge-space-*`, derivados de uma base
  compacta de 4/8px.

## Hierarquia e tipografia

- A tela deve ter um foco operacional principal; ações secundárias usam
  `btn-outline-*` ou ficam em overflow.
- Cabeçalhos usam ícone de contexto, título forte e descrição curta.
- No mobile, títulos de página usam `--sge-font-xl`; o corpo permanece em
  `--sge-font-md`/`--sge-font-sm` com peso e cor para separar níveis.
- Labels de métricas e estados usam caixa alta, tamanho pequeno e peso 700;
  valores usam peso 700 e números tabulares quando aplicável.

## Padrões mobile

- Breakpoint principal: `max-width: 767.98px`.
- A navegação inferior tem área segura, links com alvo mínimo de 44px e FAB de
  50px centralizada; o conteúdo reserva espaço inferior para ela.
- Ações de cabeçalho têm altura mínima de 44px. No dashboard, ações principais
  ocupam duas colunas e o controle de privacidade fica compacto em uma linha
  própria.
- Filter bars empilham seus campos em uma coluna. Ações agrupadas podem usar
  uma grade com ação principal flexível e reset de 44px.
- Métricas usam duas colunas em telas estreitas (`col-6`) para preservar
  comparação e reduzir rolagem vertical.
- Tabelas com `data-label` e wrapper `data-table-responsive` viram cartões
  empilhados; tabelas sem estrutura semântica devem manter rolagem horizontal.
- Modais de movimentação e busca usam comportamento de bottom sheet no mobile,
  com campos grandes e foco automático.
- Todos os controles tocáveis devem ter pelo menos 44px de altura; ícones
  isolados precisam de `aria-label` e `title` quando apropriado.

## Estados e acessibilidade

- Toda tela operacional precisa contemplar carregando, vazio, erro e sucesso.
- Mensagens de estoque baixo, zerado e normal devem conservar os estados
  semânticos existentes.
- Ícones decorativos usam `aria-hidden="true"`; ações somente com ícone usam
  nome acessível.
- Respeitar `prefers-reduced-motion` e manter foco visível com
  `--sge-focus-ring`.

## Checklist visual

- Confirmar 390px e 768px sem overflow horizontal.
- Verificar que a ação primária é identificável em menos de um segundo.
- Fazer o teste de contração: a hierarquia deve continuar clara sem depender
  de bordas fortes ou excesso de cor.
- Validar estados vazios e tabelas com dados reais, não apenas o estado ideal.
