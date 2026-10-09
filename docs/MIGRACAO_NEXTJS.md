# Relatório: Migração Full-Stack para Next.js + Vercel

Este relatório analisa a viabilidade, os impactos arquiteturais e o esforço necessário para **eliminar completamente o Django** e migrar o Sistema de Gestão de Estoque (SGE) para uma arquitetura baseada 100% em **Next.js**, com deploy na plataforma **Vercel**.

---

## 1. O que muda na Arquitetura?

A transição de um modelo tradicional com servidor persistente (Django + SQLite local) para um modelo **Serverless (Vercel)** exige mudanças fundamentais em toda a infraestrutura:

| Componente | Como é hoje (Django) | Como será no Next.js (Vercel) |
| :--- | :--- | :--- |
| **Linguagem Backend** | Python | TypeScript (Server Actions / API Routes) |
| **Banco de Dados** | SQLite local (`data/db.sqlite3`) | PostgreSQL remoto (Vercel Postgres, Supabase ou Neon) ou Turso (SQLite Edge) |
| **Acesso a Dados (ORM)** | Django ORM | Prisma ORM ou Drizzle ORM |
| **Autenticação** | `django.contrib.auth` (Sessões) | Auth.js (NextAuth) ou Clerk (JWT/Sessões) |
| **Execução de Servidor** | Processo contínuo (Gunicorn/Docker) | Serverless Functions (Funções efêmeras, sob demanda) |
| **Armazenamento de Arquivos** | Disco local / WhiteNoise | Vercel Blob Storage ou Amazon S3 |

---

## 2. Desafios e Aspectos Críticos da Migração

### A. O fim do Banco de Dados SQLite Local
**O Problema:** A Vercel utiliza uma infraestrutura *Serverless*. Isso significa que não existe um servidor rodando 24 horas. As funções são criadas sob demanda e destruídas segundos depois, o que significa que o disco (onde fica o seu arquivo `db.sqlite3`) é **efêmero (apagado a cada execução)**. 
**A Solução:** Você obrigatoriamente precisará migrar os dados atuais do SQLite para um banco de dados hospedado em nuvem. A opção mais nativa é o **Vercel Postgres** ou o **Supabase** (PostgreSQL).

### B. Transações e Concorrência de Estoque
**O Problema:** No Django, as entradas e saídas usam `transaction.atomic()` e `select_for_update()` para impedir que dois usuários vendam o mesmo último rolo de tecido ao mesmo tempo (Race Conditions). Em ambientes *Serverless*, gerenciar o "pool de conexões" e transações simultâneas no banco de dados exige muito cuidado para não esgotar as conexões da nuvem.
**A Solução:** Utilizar um ORM moderno como o Prisma com conexão via *Prisma Accelerate* ou PgBouncer configurado nativamente no Vercel Postgres para suportar transações robustas.

### C. Reescrevendo Regras de Negócio e Integrações
O Django concentra regras de negócio cruciais:
1. **Integração com Omie:** O cliente JSON-RPC (`omie_client.py`) foi todo modelado em Python. Teria que ser **totalmente reescrito** e tipado do zero em TypeScript.
2. **Signals (`post_save`):** No Django, sempre que um preço muda, um histórico (`HistoricoPreco`) é salvo "magicamente" por baixo dos panos. No Next.js, esse padrão de "gatilhos" terá que ser implementado manualmente nas Server Actions, envolvendo todas as atualizações de preço.
3. **Fechamento Mensal:** A lógica de cálculo transacional e espelhamento de dados (Snapshots) do fechamento também precisará ser convertida para Node.js.

---

## 3. Vantagens (Por que fazer?)

1. **Deploy de "Um Clique":** A experiência de deploy na Vercel é imbatível. A cada commit no GitHub (`git push`), a Vercel compila e coloca o sistema no ar automaticamente, gerando URLs de preview. Adeus, Docker e configurações manuais de Nginx/Caddy!
2. **Código Isomórfico (Tudo TypeScript):** Você terá apenas uma linguagem no projeto inteiro. Os tipos do Banco de Dados (ex: interface `Produto`) criados no backend podem ser importados e usados diretamente nos componentes React do frontend, reduzindo bugs absurdamente.
3. **Escalabilidade Automática:** Se o seu sistema tiver picos de 1.000 usuários acessando o estoque ao mesmo tempo, a Vercel escala as funções serverless instantaneamente, sem travar o servidor (desde que o banco de dados aguente).
4. **Fim de preocupações com infraestrutura de rede:** Certificados HTTPS renovam sozinhos, CDN Edge é configurada magicamente pela Vercel.

---

## 4. Conclusão e Próximos Passos (Caso decida seguir)

**O veredito:** É uma transição que levará o projeto a uma stack incrivelmente moderna e fácil de manter a longo prazo (apenas TypeScript e deploys instantâneos). Contudo, **trata-se de reescrever 100% do backend atual.** 

Se você decidir prosseguir, o **Plano de Ação** recomendado seria:

1. **Setup Inicial:** Criar um projeto Next.js (App Router) e instalar Tailwind, Shadcn/UI e Prisma.
2. **Modelagem do Banco:** Traduzir os modelos do `models.py` para o arquivo `schema.prisma`.
3. **Migração de Dados:** Criar um script (provavelmente em Python mesmo) que conecte no `db.sqlite3` antigo e despeje os dados já modelados no novo PostgreSQL da Vercel (Supabase).
4. **Camada de Autenticação:** Implementar o Auth.js (NextAuth) com provedor de email/senha ou OAuth.
5. **Portar o Frontend Atual:** As páginas que hoje estão na pasta `frontend/src/` podem ser trazidas quase que 1:1 para o Next.js, trocando as requisições (que hoje usam o Axios/fetch pro Django) diretamente para as **Server Actions** do Next.js.
6. **Reescrita da Integração Omie:** Construir o SDK Omie em TypeScript.
