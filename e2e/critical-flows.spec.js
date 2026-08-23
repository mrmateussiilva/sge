const { test, expect } = require('@playwright/test');

const { password, users } = require('./test-data');

async function loginAs(page, username) {
    await page.goto('/accounts/login/');
    await page.getByLabel('Usuário').fill(username);
    await page.locator('#id_password').fill(password);
    await page.getByRole('button', { name: 'Entrar' }).click();
    await expect(page).toHaveURL(/\/$/);
}

async function selectProduct(page, description) {
    const option = page.locator('#select-produto-mov option').filter({ hasText: description }).first();
    const value = await option.getAttribute('value');
    await expect(value).not.toBeNull();
    await page.locator('#select-produto-mov').selectOption(value);
}

test.describe('Fluxos críticos do SGE', () => {
    test('usuário somente leitura não vê ações operacionais', async ({ page }) => {
        await loginAs(page, users.leitura);

        await page.goto('/produtos/');
        await expect(page.getByRole('heading', { name: 'Produtos' })).toBeVisible();
        await expect(page.getByRole('link', { name: 'Novo Produto' })).toHaveCount(0);
        await expect(page.locator('#formImportarCSV')).toHaveCount(0);

        await page.goto('/movimentacao/');
        await expect(page.getByText('Você está em modo somente leitura.')).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Nova movimentação' })).toHaveCount(0);
        await expect(page.locator('#globalMoveForm')).toHaveCount(0);
    });

    test('operador registra uma entrada de estoque pela interface', async ({ page }) => {
        await loginAs(page, users.operador);
        await page.goto('/movimentacao/');

        await selectProduct(page, 'E2E Produto Movimento');
        await page.locator('#input-quantidade-mov').fill('2');

        const responsePromise = page.waitForResponse(response => (
            response.url().includes('/movimentacao/') &&
            response.request().method() === 'POST'
        ));
        await page.getByRole('button', { name: 'Registrar movimentação' }).click();
        const response = await responsePromise;

        expect(response.ok()).toBeTruthy();
        await expect(page.locator('#historico-movimentacoes').getByText('E2E Produto Movimento')).toBeVisible();
    });

    test('operador recebe uma ordem aprovada e o fluxo termina como recebida', async ({ page }) => {
        await loginAs(page, users.operador);
        await page.goto('/ordens/');

        await page.getByRole('link', { name: 'Ver detalhes' }).first().click();
        await expect(page).toHaveURL(/\/ordem\/\d+\/$/);
        await expect(page.getByRole('button', { name: 'Receber no Estoque' })).toBeVisible();

        await page.getByRole('button', { name: 'Receber no Estoque' }).click();
        await expect(page.locator('#modalConfirmar')).toBeVisible();

        const responsePromise = page.waitForResponse(response => (
            response.url().includes('/receber/') &&
            response.request().method() === 'POST'
        ));
        await page.locator('#modalConfirmarBtn').click();
        const response = await responsePromise;

        expect(response.ok()).toBeTruthy();
        await expect(page.getByText('Recebida')).toBeVisible();
    });

    test('administrador acessa a configuração Omie sem exibir o segredo', async ({ page }) => {
        await loginAs(page, users.admin);
        await page.goto('/omie/notas/');

        const configButton = page.getByRole('button', { name: /Configurar API Omie/ });
        await expect(configButton).toBeVisible();
        await configButton.click();
        await expect(page.locator('#omie-app-secret')).toBeVisible();
        await expect(page.locator('#omie-app-secret')).toHaveAttribute('type', 'password');
        await expect(page.locator('#omie-app-secret')).toHaveValue('');
    });
});
