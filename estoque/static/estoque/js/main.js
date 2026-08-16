/**
 * SGE - Main JavaScript Bundle
 * Suporte global para sidebar, busca global (Ctrl+K), temas, HTMX feedback e FAB de movimentação.
 */

function showToast(message, type) {
    type = type || 'success';
    const el = document.getElementById('liveToast');
    if (!el) return;
    el.className = 'toast border-0 bg-' + type + ' text-white';
    const msgEl = document.getElementById('toastMessage');
    if (msgEl) msgEl.textContent = message;
    if (window.bootstrap && window.bootstrap.Toast) {
        window.bootstrap.Toast.getOrCreateInstance(el).show();
    }
}

// Chart.js Lifecycle Manager (HTMX Swap Safety)
window.sgeCharts = window.sgeCharts || {};

function registerChart(id, chartInstance) {
    if (window.sgeCharts[id]) {
        try { window.sgeCharts[id].destroy(); } catch (e) {}
    }
    window.sgeCharts[id] = chartInstance;
}

function destroyAllCharts() {
    Object.keys(window.sgeCharts).forEach(function(key) {
        if (window.sgeCharts[key]) {
            try { window.sgeCharts[key].destroy(); } catch (e) {}
            delete window.sgeCharts[key];
        }
    });
}

document.addEventListener('htmx:beforeSwap', function(evt) {
    var requestConfig = evt.detail.requestConfig || {};
    if (requestConfig.boosted && evt.detail.target === document.body) {
        var responseDocument = new DOMParser().parseFromString(evt.detail.serverResponse, 'text/html');
        var responseMain = responseDocument.getElementById('main-content');
        var currentMain = document.getElementById('main-content');

        if (responseMain && currentMain) {
            evt.detail.target = currentMain;
            evt.detail.serverResponse = responseMain.innerHTML;
            if (responseDocument.title) document.title = responseDocument.title;
        }
    }

    if (evt.detail.target && (evt.detail.target.id === 'main-content' || evt.detail.target === document.body)) {
        destroyAllCharts();
    }
});

// Mobile drawer toggle & backdrop logic
function toggleSidebar() {
    var sidebar = document.getElementById('sidebar-wrapper');
    var backdrop = document.getElementById('sidebar-backdrop');
    if (!sidebar || !backdrop) return;
    var isMobile = window.innerWidth < 992;
    
    if (isMobile) {
        var isOpen = sidebar.classList.contains('show-mobile');
        if (isOpen) {
            closeMobileSidebar();
        } else {
            backdrop.style.display = 'block';
            setTimeout(function() { backdrop.classList.add('show'); }, 10);
            sidebar.classList.add('show-mobile');
        }
    } else {
        sidebar.classList.toggle('collapsed');
    }
}

function closeMobileSidebar() {
    var sidebar = document.getElementById('sidebar-wrapper');
    var backdrop = document.getElementById('sidebar-backdrop');
    if (!sidebar || !backdrop) return;
    sidebar.classList.remove('show-mobile');
    backdrop.classList.remove('show');
    setTimeout(function() { backdrop.style.display = 'none'; }, 200);
}

document.addEventListener('DOMContentLoaded', function() {
    var menuToggle = document.getElementById('menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }

    var closeBtn = document.getElementById('close-mobile-menu');
    if (closeBtn) {
        closeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            closeMobileSidebar();
        });
    }

    var backdrop = document.getElementById('sidebar-backdrop');
    if (backdrop) {
        backdrop.addEventListener('click', function() {
            closeMobileSidebar();
        });
    }

    document.querySelectorAll('#sidebar-wrapper .nav-link-custom').forEach(function(link) {
        link.addEventListener('click', function() {
            closeMobileSidebar();
        });
    });
});

function setHtmxRequestState(source, active) {
    if (!source) return;
    var button = source.matches && source.matches('button, [type="submit"]')
        ? source
        : source.querySelector && source.querySelector('button[type="submit"], input[type="submit"]');
    if (!button) return;
    button.disabled = active;
    button.classList.toggle('sge-request-active', active);
    button.setAttribute('aria-busy', active ? 'true' : 'false');
}

document.addEventListener('htmx:beforeRequest', function(evt) {
    var target = evt.detail.target;
    var isPageNavigation = target && (target.id === 'main-content' || target === document.body);
    if (isPageNavigation && evt.detail.elt.dataset.sgeLoading !== 'inline') {
        var overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.add('show');
    }
    setHtmxRequestState(evt.detail.elt, true);
});

document.addEventListener('htmx:afterRequest', function(evt) {
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.remove('show');
    setHtmxRequestState(evt.detail.elt, false);
});

function resetMovementFields(form) {
    var quantidade = form.querySelector('[name="quantidade"]');
    var observacao = form.querySelector('[name="observacao"]');
    var entrada = form.querySelector('[name="tipo"][value="ENTRADA"]');
    var produto = form.querySelector('[name="produto_id"]');

    if (quantidade) quantidade.value = '';
    if (observacao) observacao.value = '';
    if (entrada) entrada.checked = true;
    if (produto && window.htmx) window.htmx.trigger(produto, 'change');
}

document.addEventListener('htmx:responseError', function(evt) {
    showToast('Não foi possível concluir a operação. Tente novamente.', 'danger');
});

document.addEventListener('htmx:targetError', function(evt) {
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.remove('show');
    var source = evt.detail && evt.detail.elt;
    var selector = evt.detail && evt.detail.target;
    console.error('Alvo HTMX não encontrado.', {
        selector: selector,
        element: source,
    });
    showToast('A área da página não está disponível. Atualize e tente novamente.', 'danger');
});

document.addEventListener('htmx:sendError', function() {
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.remove('show');
    showToast('Falha de conexão com o servidor.', 'danger');
});

document.addEventListener('htmx:timeout', function() {
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.remove('show');
    showToast('A operação demorou mais que o esperado. Tente novamente.', 'warning');
});

function updateActiveSidebarLink() {
    var path = window.location.pathname;
    document.querySelectorAll('#sidebar-wrapper .nav-link-custom').forEach(function(link) {
        var href = link.getAttribute('href');
        if (!href || href === '#') return;
        if (href === '/' && path === '/') {
            link.classList.add('active');
        } else if (href !== '/' && (path === href || path.startsWith(href))) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

document.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target && evt.detail.target.id === 'produtos-conteudo') {
        var filterForm = document.getElementById('produtos-filter-form');
        var content = document.getElementById('produtos-conteudo');
        if (filterForm && content) {
            var abaInput = filterForm.querySelector('[name="aba"]');
            var sortInput = filterForm.querySelector('[name="sort"]');
            var directionInput = filterForm.querySelector('[name="dir"]');
            if (abaInput) abaInput.value = content.dataset.aba || '';
            if (sortInput) sortInput.value = content.dataset.sort || '';
            if (directionInput) directionInput.value = content.dataset.direction || '';
        }
    }

    if (evt.detail.target && (evt.detail.target.id === 'main-content' || evt.detail.target === document.body)) {
        updateActiveSidebarLink();
        closeMobileSidebar();
        var mainContent = document.getElementById('main-content');
        if (mainContent) mainContent.scrollTop = 0;
    }
});
document.addEventListener('htmx:historyRestore', updateActiveSidebarLink);

// Dark mode sync
(function() {
    var toggle = document.getElementById('darkModeToggle');
    var toggleHeader = document.getElementById('darkModeToggleHeader');
    var icon = toggle ? toggle.querySelector('i') : null;
    var iconHeader = toggleHeader ? toggleHeader.querySelector('i') : null;
    var label = document.getElementById('darkModeLabel');
    var html = document.documentElement;
    
    function applyTheme(isDark) {
        if (isDark) {
            html.setAttribute('data-bs-theme', 'dark');
            if (icon) icon.className = 'bi bi-sun me-1';
            if (iconHeader) iconHeader.className = 'bi bi-sun';
            if (label) label.textContent = 'Modo Claro';
            localStorage.setItem('sgeDarkMode', 'true');
        } else {
            html.removeAttribute('data-bs-theme');
            if (icon) icon.className = 'bi bi-moon-stars me-1';
            if (iconHeader) iconHeader.className = 'bi bi-moon-stars';
            if (label) label.textContent = 'Modo Escuro';
            localStorage.setItem('sgeDarkMode', 'false');
        }
    }

    var stored = localStorage.getItem('sgeDarkMode') === 'true';
    applyTheme(stored);

    document.addEventListener('DOMContentLoaded', function() {
        var toggleBtn = document.getElementById('darkModeToggle');
        var toggleHeaderBtn = document.getElementById('darkModeToggleHeader');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', function() {
                applyTheme(html.getAttribute('data-bs-theme') !== 'dark');
            });
        }
        if (toggleHeaderBtn) {
            toggleHeaderBtn.addEventListener('click', function() {
                applyTheme(html.getAttribute('data-bs-theme') !== 'dark');
            });
        }
    });
})();

// Busca Global (Ctrl+K)
function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function productMetaText(p) {
    return p.tipo_produto + ' | Estoque: ' + p.quantidade;
}

function renderProductLinkResults(container, produtos) {
    container.innerHTML = '';
    const list = document.createElement('div');
    list.className = 'list-group list-group-flush';
    produtos.forEach(p => {
        const a = document.createElement('a');
        a.href = `/produto/${p.id}/`;
        a.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-3 py-2';
        a.innerHTML = `
            <div class="min-width-0">
                <div class="fw-medium text-truncate">${escapeHtml(p.descricao)}</div>
                <div class="small text-muted">${escapeHtml(productMetaText(p))}</div>
            </div>
            <i class="bi bi-chevron-right text-muted flex-shrink-0"></i>
        `;
        list.appendChild(a);
    });
    container.appendChild(list);
}

function getCookie(name) {
    const cookie = document.cookie
        .split(';')
        .map(value => value.trim())
        .find(value => value.startsWith(name + '='));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : '';
}

document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('global-search-input');
        if (searchInput) searchInput.focus();
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('global-search-input');
    const searchResults = document.getElementById('global-search-results');
    const mobileSearchToggle = document.getElementById('mobileSearchToggle');
    const mobileSearchInput = document.getElementById('mobile-search-input');
    const mobileSearchResults = document.getElementById('mobile-search-results');
    const mobileSearchEmpty = document.getElementById('mobile-search-empty');
    let mobileSearchModal;

    if (searchInput && searchResults) {
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const q = e.target.value.trim();
            if (q.length < 2) {
                searchResults.classList.add('d-none');
                return;
            }
            searchTimeout = setTimeout(() => {
                fetch(`/busca-rapida/?q=${encodeURIComponent(q)}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.resultados.length === 0) {
                            searchResults.innerHTML = '<div class="p-3 text-muted text-center small">Nenhum produto encontrado.</div>';
                        } else {
                            renderProductLinkResults(searchResults, data.resultados);
                        }
                        searchResults.classList.remove('d-none');
                    });
            }, 300);
        });

        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.add('d-none');
            }
        });
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim().length >= 2) searchResults.classList.remove('d-none');
        });
    }

    if (mobileSearchToggle && mobileSearchInput && mobileSearchResults) {
        const modalEl = document.getElementById('mobileSearchModal');
        if (modalEl && window.bootstrap) {
            mobileSearchModal = new window.bootstrap.Modal(modalEl);
            mobileSearchToggle.addEventListener('click', function() {
                mobileSearchInput.value = '';
                mobileSearchResults.innerHTML = '';
                mobileSearchResults.classList.add('d-none');
                if (mobileSearchEmpty) mobileSearchEmpty.classList.add('d-none');
                mobileSearchModal.show();
                setTimeout(function() { mobileSearchInput.focus(); }, 250);
            });

            let mobileSearchTimeout;
            mobileSearchInput.addEventListener('input', function(e) {
                clearTimeout(mobileSearchTimeout);
                const q = e.target.value.trim();
                mobileSearchResults.classList.add('d-none');
                if (mobileSearchEmpty) mobileSearchEmpty.classList.add('d-none');
                if (q.length < 2) return;

                mobileSearchTimeout = setTimeout(function() {
                    fetch(`/busca-rapida/?q=${encodeURIComponent(q)}`)
                        .then(r => r.json())
                        .then(data => {
                            if (data.resultados.length === 0) {
                                mobileSearchResults.innerHTML = '';
                                if (mobileSearchEmpty) mobileSearchEmpty.classList.remove('d-none');
                                return;
                            }
                            renderProductLinkResults(mobileSearchResults, data.resultados);
                            mobileSearchResults.classList.remove('d-none');
                        })
                        .catch(() => {
                            mobileSearchResults.innerHTML = '<div class="p-3 text-danger text-center small">Erro ao buscar produtos.</div>';
                            mobileSearchResults.classList.remove('d-none');
                        });
                }, 250);
            });
        }
    }

    // Modal Movimentação Rápida Global (FAB)
    let globalMoveModal;
    const gModalEl = document.getElementById('globalMoveModal');
    if (gModalEl && window.bootstrap) {
        globalMoveModal = new window.bootstrap.Modal(gModalEl);
    }

    window.openGlobalMoveModal = function(produtoId = null, produtoNome = null) {
        const form = document.getElementById('globalMoveForm');
        if (!form) return;
        form.reset();
        window.clearGlobalMoveProduto();
        
        if (produtoId && produtoNome) {
            document.getElementById('globalMoveProdutoId').value = produtoId;
            document.getElementById('globalMoveSelectedName').textContent = produtoNome;
            document.getElementById('globalMoveSelectedMeta').textContent = '';
            document.getElementById('globalMoveProdutoSearch').classList.add('d-none');
            document.getElementById('globalMoveSelectedProduto').classList.remove('d-none');
        }
        updateGlobalMoveSubmitLabel();
        if (globalMoveModal) globalMoveModal.show();
    };

    window.clearGlobalMoveProduto = function() {
        const pId = document.getElementById('globalMoveProdutoId');
        const pSearch = document.getElementById('globalMoveProdutoSearch');
        const pMeta = document.getElementById('globalMoveSelectedMeta');
        const pSel = document.getElementById('globalMoveSelectedProduto');
        const pRes = document.getElementById('globalMoveSearchResults');
        if (pId) pId.value = '';
        if (pSearch) pSearch.value = '';
        if (pMeta) pMeta.textContent = '';
        if (pSearch) pSearch.classList.remove('d-none');
        if (pSel) pSel.classList.add('d-none');
        if (pRes) pRes.classList.add('d-none');
        if (pSearch) pSearch.focus();
    };

    function updateGlobalMoveSubmitLabel() {
        const tipoEl = document.getElementById('globalMoveTipo');
        const btn = document.getElementById('globalMoveSubmitBtn');
        if (tipoEl && btn) {
            btn.textContent = tipoEl.value === 'SAIDA' ? 'Registrar saída' : 'Registrar entrada';
        }
    }

    const globalMoveSearch = document.getElementById('globalMoveProdutoSearch');
    const globalMoveResults = document.getElementById('globalMoveSearchResults');
    
    if (globalMoveSearch && globalMoveResults) {
        let gmSearchTimeout;
        globalMoveSearch.addEventListener('input', (e) => {
            clearTimeout(gmSearchTimeout);
            const q = e.target.value.trim();
            if (q.length < 2) {
                globalMoveResults.classList.add('d-none');
                return;
            }
            gmSearchTimeout = setTimeout(() => {
                fetch(`/busca-rapida/?q=${encodeURIComponent(q)}`)
                    .then(r => r.json())
                    .then(data => {
                        globalMoveResults.innerHTML = '';
                        if (data.resultados.length > 0) {
                            const list = document.createElement('div');
                            list.className = 'list-group list-group-flush';
                            data.resultados.forEach(p => {
                                const btn = document.createElement('button');
                                btn.type = 'button';
                                btn.className = 'list-group-item list-group-item-action py-2 text-start';
                                btn.innerHTML = `<span class="fw-medium d-block text-truncate">${escapeHtml(p.descricao)}</span><small class="text-muted">${escapeHtml(productMetaText(p))}</small>`;
                                btn.onclick = () => {
                                    document.getElementById('globalMoveProdutoId').value = p.id;
                                    document.getElementById('globalMoveSelectedName').textContent = p.descricao;
                                    document.getElementById('globalMoveSelectedMeta').textContent = productMetaText(p);
                                    globalMoveSearch.classList.add('d-none');
                                    document.getElementById('globalMoveSelectedProduto').classList.remove('d-none');
                                    globalMoveResults.classList.add('d-none');
                                };
                                list.appendChild(btn);
                            });
                            globalMoveResults.appendChild(list);
                            globalMoveResults.classList.remove('d-none');
                        } else {
                            globalMoveResults.innerHTML = '<div class="p-2 text-muted small text-center">Não encontrado</div>';
                            globalMoveResults.classList.remove('d-none');
                        }
                    });
            }, 300);
        });
    }

    document.getElementById('globalMoveTipo')?.addEventListener('change', updateGlobalMoveSubmitLabel);

    document.getElementById('globalMoveForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const pid = document.getElementById('globalMoveProdutoId').value;
        if (!pid) {
            showToast('Selecione um produto para movimentar.', 'danger');
            return;
        }
        const btn = document.getElementById('globalMoveSubmitBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';

        const payload = {
            produto_id: pid,
            tipo: document.getElementById('globalMoveTipo').value,
            quantidade: parseFloat(document.getElementById('globalMoveQuantidade').value),
            observacao: document.getElementById('globalMoveObservacao').value
        };

        const csrfTokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
        const token = csrfTokenElement ? csrfTokenElement.value : getCookie('csrftoken');

        fetch('/movimentacao/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            },
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                showToast('Movimentação registrada com sucesso!');
                if (globalMoveModal) globalMoveModal.hide();
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showToast(data.erro || 'Erro ao salvar movimentação.', 'danger');
            }
        })
        .catch(() => showToast('Erro de rede.', 'danger'))
        .finally(() => {
            btn.disabled = false;
            updateGlobalMoveSubmitLabel();
        });
    });
});
