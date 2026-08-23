module.exports = {
    password: process.env.E2E_PASSWORD || 'sge-e2e-local-2026',
    users: {
        operador: 'e2e_operador',
        leitura: 'e2e_leitura',
        admin: 'e2e_admin',
    },
};
