const { test, expect } = require('@playwright/test');
const { password, users } = require('./test-data');

async function login(page) {
    await page.goto('/accounts/login/');
    await page.getByLabel('Usuário').fill(users.admin);
    await page.locator('#id_password').fill(password);
    await page.getByRole('button', { name: 'Entrar' }).click();
    await page.waitForURL('/');
}

async function post(page, endpoint, data) {
    const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken').value;
    const response = await page.request.post(endpoint, { data, headers: { 'X-CSRFToken': csrf } });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
}

test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    await login(page);
    // Catalog larger than the old selector's hard limit. Setup uses the real API.
    for (let index = 0; index < 101; index++) {
        await post(page, '/api/v1/produtos/cadastrar/', {
            descricao: `AAA Catálogo SPA ${String(index).padStart(3, '0')}`,
            tipo_produto: 'OUTRO', unidade_medida: 'UN',
        });
    }
    await page.close();
});

for (const [device, viewport] of [['desktop', { width: 1280, height: 900 }], ['mobile', { width: 390, height: 844 }]]) {
    test.describe(device, () => {
        test.use({ viewport });
        test.beforeEach(async ({ page }) => login(page));

        test('edição preserva vínculos, unidade, zeros e valores ausentes', async ({ page }) => {
            const categoria = await post(page, '/api/v1/categorias/salvar/', { nome: `Categoria SPA ${device}`, cor: '#123456' });
            const opcoes = await (await page.request.get('/api/v1/produtos/opcoes/')).json();
            const categoriaId = categoria.id || opcoes.categorias.find(item => item.nome === `Categoria SPA ${device}`).id;
            const fornecedorId = opcoes.fornecedores[0].id;
            await post(page, '/api/v1/produtos/cadastrar/', {
                descricao: `ZZZ Edição SPA ${device}`, tipo_produto: 'OUTRO', unidade_medida: 'KG',
                fornecedor_id: fornecedorId, categoria_id: categoriaId, quantidade_base: '10',
                preco_custo: '0', preco_venda: null, estoque_minimo: '0',
            });
            const lista = await (await page.request.get(`/api/v1/produtos/?aba=TODOS&busca=ZZZ%20Edição%20SPA%20${device}`)).json();
            const id = lista.itens[0].id;
            if (device === 'desktop') {
                await page.goto(`/app/produtos?aba=OUTRO&busca=${encodeURIComponent(`ZZZ Edição SPA ${device}`)}`);
                await page.getByTitle('Editar informações').click();
            } else {
                await page.goto(`/app/produtos/${id}`);
                await page.getByRole('button', { name: /Editar/ }).click();
            }
            const descricao = page.getByPlaceholder('Ex: Papel Sublimático 90g Bobina 1,60m');
            await expect(descricao).toHaveValue(`ZZZ Edição SPA ${device}`);
            await descricao.fill(`ZZZ Edição SPA ${device} alterada`);
            const saved = page.waitForResponse(response => response.url().endsWith(`/produtos/${id}/editar/`) && response.request().method() === 'POST');
            await page.getByRole('button', { name: 'Salvar Alterações' }).click();
            expect((await saved).ok()).toBeTruthy();
            const detalhe = await (await page.request.get(`/api/v1/produtos/${id}/`)).json();
            expect(detalhe.produto).toMatchObject({
                descricao: `ZZZ Edição SPA ${device} alterada`, unidade_medida: 'KG',
                fornecedor: { id: fornecedorId }, categoria: { id: categoriaId },
                preco_custo: 0, preco_venda: null, estoque_minimo: 0, quantidade: 10,
            });
            expect(detalhe.movimentacoes).toHaveLength(1);
            expect(detalhe.movimentacoes[0].quantidade_formatada).toBe('10,00 kg');
        });

        test('movimentação encontra produto além dos primeiros cem', async ({ page }) => {
            const nome = `ZZZ Movimento SPA ${device}`;
            await post(page, '/api/v1/produtos/cadastrar/', { descricao: nome, tipo_produto: 'OUTRO', quantidade_base: '10' });
            await page.goto('/app/movimentacoes');
            await page.getByRole('button', { name: 'Registrar Movimentação', exact: true }).click();
            const select = page.getByRole('combobox', { name: 'Selecionar insumo' });
            await expect(select).toBeEnabled();
            await expect(select.getByRole('option', { name: new RegExp(nome) })).toHaveCount(0);
            await page.getByRole('button', { name: 'Próxima', exact: true }).last().click();
            await expect(page.getByText(/^2\//)).toBeVisible();
            await page.getByRole('textbox', { name: 'Buscar insumo' }).fill(nome);
            await select.selectOption({ label: `${nome} (Saldo: 10,00 un)` });
            await page.getByPlaceholder('Ex: 10.50').fill('1');
            const saved = page.waitForResponse(response => response.url().endsWith('/movimentacoes/registrar/') && response.request().method() === 'POST');
            await page.getByRole('button', { name: 'Confirmar Saída' }).click();
            expect((await saved).ok()).toBeTruthy();
        });

        test('ordem busca itens sem perder a seleção de outras linhas', async ({ page }) => {
            const nome = `ZZZ Ordem SPA ${device}`;
            await post(page, '/api/v1/produtos/cadastrar/', { descricao: nome, tipo_produto: 'OUTRO', preco_custo: '2.50' });
            await page.goto('/app/ordens');
            await page.getByRole('button', { name: /Nova Ordem/ }).click();
            await page.getByRole('textbox', { name: 'Buscar insumo' }).fill(nome);
            const primeiro = page.getByRole('combobox', { name: 'Selecionar insumo' }).first();
            await primeiro.selectOption({ label: `${nome} (Saldo: 0,00 un)` });
            const id = await primeiro.inputValue();
            await page.getByRole('button', { name: 'Adicionar Linha' }).click();
            await page.getByRole('textbox', { name: 'Buscar insumo' }).last().fill('AAA Catálogo SPA 100');
            await page.getByRole('combobox', { name: 'Selecionar insumo' }).last().selectOption({ label: 'AAA Catálogo SPA 100 (Saldo: 0,00 un)' });
            await expect(primeiro).toHaveValue(id);
            await page.screenshot({ path: test.info().outputPath(`ordem-${device}.png`), fullPage: true });
            const saved = page.waitForResponse(response => response.url().endsWith('/ordens/criar/') && response.request().method() === 'POST');
            await page.getByRole('button', { name: 'Criar Ordem de Compra' }).click();
            const response = await saved;
            expect(response.ok()).toBeTruthy();
            const ordem = await response.json();
            const detalhe = await (await page.request.get(`/api/v1/ordens/${ordem.id}/`)).json();
            expect(detalhe.itens).toHaveLength(2);
            expect(detalhe.itens[0]).toMatchObject({ produto_id: Number(id), preco_unitario: 2.5 });
        });
    });
}
