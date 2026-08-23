const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
    testDir: './e2e',
    testMatch: '**/*.spec.js',
    fullyParallel: false,
    workers: 1,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    reporter: process.env.CI ? [['line'], ['html', { open: 'never' }]] : 'list',
    timeout: 30_000,
    expect: { timeout: 5_000 },
    use: {
        baseURL: process.env.BASE_URL || 'http://127.0.0.1:8001',
        actionTimeout: 10_000,
        navigationTimeout: 15_000,
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',
        locale: 'pt-BR',
        timezoneId: 'America/Sao_Paulo',
        ...devices['Desktop Chrome'],
    },
    webServer: {
        command: 'bash e2e/run-server.sh',
        url: 'http://127.0.0.1:8001/accounts/login/',
        reuseExistingServer: false,
        timeout: 120_000,
        stdout: 'pipe',
        stderr: 'pipe',
    },
});
