/* js/views/importarXml.js */
window.renderImportarXml = async function () {
    const appContent = document.getElementById("app-content");

    appContent.innerHTML = `
    <!-- Header -->
    <header class="mb-3">
      <h1 class="page-title fs-4 fw-bold mb-0 text-dark">Importar XML</h1>
      <p class="text-secondary small mb-0 mt-1">Importe produtos automaticamente a partir de notas fiscais</p>
    </header>

    <div class="row g-3">
        <!-- Coluna de Upload -->
        <div class="col-lg-4 col-xl-3">
            <div class="card-enterprise h-100 bg-white border shadow-sm" style="border-radius: var(--radius-md);">
                <div class="card-header-polished border-bottom px-3 py-2 bg-white" style="border-top-left-radius: var(--radius-md); border-top-right-radius: var(--radius-md);">
                    <h6 class="fw-bold mb-0 text-dark" style="font-size: 0.85rem">Origem do XML</h6>
                </div>
                <div class="p-4 d-flex flex-column align-items-center justify-content-center text-center gap-3">
                    
                    <!-- Tabs de seleção -->
                    <ul class="nav nav-pills mb-3 w-100" role="tablist">
                        <li class="nav-item flex-fill" role="presentation">
                            <button class="nav-link active w-100" id="tabArquivo-tab" data-bs-toggle="tab" data-bs-target="#tabArquivo" type="button" role="tab">
                                <i class="bi bi-file-earmark me-1"></i> Arquivo
                            </button>
                        </li>
                        <li class="nav-item flex-fill" role="presentation">
                            <button class="nav-link w-100" id="tabLink-tab" data-bs-toggle="tab" data-bs-target="#tabLink" type="button" role="tab">
                                <i class="bi bi-link-45deg me-1"></i> Link/URL
                            </button>
                        </li>
                    </ul>

                    <!-- Tab Arquivo -->
                    <div class="tab-content w-100">
                        <div class="tab-pane fade show active" id="tabArquivo" role="tabpanel">
                            <div class="bg-light rounded-circle d-flex align-items-center justify-content-center border" style="width: 60px; height: 60px;">
                               <i class="bi bi-filetype-xml fs-3 text-secondary"></i>
                            </div>
                            <div>
                                <label for="xmlFileInput" class="form-label d-none">Escolha o XML</label>
                                <input class="form-control form-control-sm mb-2" type="file" id="xmlFileInput" accept=".xml">
                                <small class="text-muted d-block" style="font-size: 0.70rem;">Apenas arquivos XML assinados pela SEFAZ</small>
                            </div>
                        </div>
                        <div class="tab-pane fade" id="tabLink" role="tabpanel">
                            <div class="bg-light rounded-circle d-flex align-items-center justify-content-center border" style="width: 60px; height: 60px;">
                               <i class="bi bi-cloud-download fs-3 text-secondary"></i>
                            </div>
                            <div class="w-100 text-start">
                                <label for="xmlUrlInput" class="form-label small fw-medium">URL do XML</label>
                                <textarea class="form-control form-control-sm mb-2" id="xmlUrlInput" rows="3" placeholder="Cole aqui o link do XML (https://...)"></textarea>
                                <small class="text-muted d-block" style="font-size: 0.70rem;">Cole a URL completa do arquivo XML para download automático</small>
                            </div>
                        </div>
                    </div>

                    <button class="btn btn-primary shadow-sm w-100 mt-2" id="btnProcessarXml" disabled>
                        <i class="bi bi-gear me-2"></i> Processar XML
                    </button>
                </div>
            </div>
        </div>

        <!-- Coluna Preview da Nota e Itens -->
        <div class="col-lg-8 col-xl-9 d-flex flex-column gap-3">
            
            <!-- Resumo da Nota -->
            <div class="card-enterprise bg-white border shadow-sm" id="notaResumoCard" style="display: none; border-radius: var(--radius-md);">
                <div class="card-header-polished border-bottom px-3 py-2 bg-white d-flex justify-content-between align-items-center" style="border-top-left-radius: var(--radius-md); border-top-right-radius: var(--radius-md);">
                    <h6 class="fw-bold mb-0 text-dark" style="font-size: 0.85rem">Dados da Nota Fisca</h6>
                    <span class="badge border bg-light text-secondary font-monospace fw-medium" id="notaChaveAcesso" style="font-size: 0.7rem;"></span>
                </div>
                <div class="p-3">
                    <div class="row g-2">
                        <div class="col-sm-6 col-md-3">
                            <span class="d-block text-muted text-uppercase mb-1" style="font-size: 0.65rem; font-weight: 600;">Número / Série</span>
                            <strong class="text-dark fs-6 lh-1" id="notaNumeroSerie">-</strong>
                        </div>
                        <div class="col-sm-6 col-md-4">
                            <span class="d-block text-muted text-uppercase mb-1" style="font-size: 0.65rem; font-weight: 600;">Fornecedor</span>
                            <div class="text-dark fw-bold text-truncate lh-1" style="font-size: 0.85rem;" id="notaFornecedor"></div>
                            <span class="text-muted font-monospace" style="font-size: 0.65rem;" id="notaCnpj"></span>
                        </div>
                        <div class="col-sm-6 col-md-3">
                            <span class="d-block text-muted text-uppercase mb-1" style="font-size: 0.65rem; font-weight: 600;">Emissão</span>
                            <strong class="text-dark lh-1" style="font-size: 0.85rem;" id="notaEmissao">-</strong>
                        </div>
                        <div class="col-sm-6 col-md-2 text-md-end">
                            <span class="d-block text-muted text-uppercase mb-1" style="font-size: 0.65rem; font-weight: 600;">Valor Total</span>
                            <strong class="text-primary fs-6 lh-1" id="notaValorTotal">-</strong>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Produtos Parsed -->
            <div class="card-enterprise bg-white border shadow-sm flex-grow-1 d-flex flex-column" id="produtosResumoCard" style="border-radius: var(--radius-md);">
                <div class="card-header-polished border-bottom px-3 py-2 bg-white d-flex justify-content-between align-items-center" style="border-top-left-radius: var(--radius-md); border-top-right-radius: var(--radius-md);">
                    <h6 class="fw-bold mb-0 text-dark" style="font-size: 0.85rem">Itens Analisados</h6>
                    <button class="btn btn-sm btn-success px-3 shadow-sm fw-medium d-none" id="btnConfirmarImportacao" style="font-size: 0.75rem">
                       <i class="bi bi-check2-circle me-1"></i> Confirmar Importação
                    </button>
                </div>
                <div class="flex-grow-1 p-0 overflow-auto" id="produtosTableContainer">
                    <div class="empty-state py-5 mt-2 text-center text-muted">
                        <i class="bi bi-table mb-2 d-block" style="font-size: 2rem;"></i>
                        <h6 class="fw-bold fs-6 mb-1 text-dark">Aguardando XML</h6>
                        <small style="font-size: 0.75rem;">Os produtos extraídos aparecerão aqui.</small>
                    </div>
                </div>
            </div>

        </div>
    </div>
  `;

    let currentAnalysis = null;
    let currentFile = null;

    const inputXML = document.getElementById("xmlFileInput");
    const inputUrl = document.getElementById("xmlUrlInput");
    const btnProcessar = document.getElementById("btnProcessarXml");

    inputXML.addEventListener("change", (e) => {
        currentFile = e.target.files[0] || null;
        btnProcessar.disabled = !currentFile;
    });

    inputUrl.addEventListener("input", (e) => {
        const hasUrl = e.target.value.trim().length > 0;
        btnProcessar.disabled = !hasUrl && !currentFile;
    });

    inputUrl.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            btnProcessar.click();
        }
    });

    const generateTable = (produtos) => {
        if (produtos.length === 0) return `<div class="p-4 text-center text-muted">XML não contém produtos válidos.</div>`;

        const rows = produtos.map((p, idx) => {
            const badgeClass = p.status === "novo" ? "bg-primary-subtle text-primary border-primary-subtle" : "bg-light text-secondary border-light-subtle";
            const statusLbl = p.status === "novo" ? "Produto Novo" : "Apenas Atualizar Estoq.";

            return `
          <tr>
             <td class="ps-3 align-middle">
                 <input class="form-check-input item-check pointer" type="checkbox" data-idx="${idx}" checked>
             </td>
             <td class="align-middle">
                 <div class="fw-bold text-dark text-truncate mb-0 lh-1" style="font-size: 0.82rem; max-width: 250px;" title="${p.descricao}">${p.descricao}</div>
                 <div class="d-flex gap-2 align-items-center mt-1">
                    <span class="badge border bg-white shadow-sm text-secondary font-monospace rounded-pill" style="font-size: 0.65rem; font-weight:500; padding: 2px 6px;">${p.codigo}</span>
                    <span class="text-muted" style="font-size: 0.65rem;"><i class="bi bi-link-45deg"></i> NCM ${p.ncm}</span>
                 </div>
             </td>
             <td class="text-center align-middle">
                 <span class="badge ${badgeClass} border shadow-sm px-2 py-1" style="font-weight: 500; font-size: 0.65rem;">${statusLbl}</span>
             </td>
             <td class="text-end align-middle">
                 <strong class="text-success fs-6 lh-1">+${p.quantidade}</strong>
                 <br><small class="text-muted" style="font-size: 0.65rem;">${p.unidade}</small>
             </td>
             <td class="text-end pe-3 align-middle text-muted" style="font-size: 0.75rem;">
                 <span class="d-block">R$ ${p.valor_unitario.toFixed(2)} /un</span>
                 <strong class="text-dark">R$ ${p.valor_total.toFixed(2)}</strong>
             </td>
          </tr>
          `;
        }).join("");

        return `
        <div class="table-responsive">
          <table class="table table-compact mb-0 border-0">
             <thead class="position-sticky top-0 bg-white" style="z-index: 1;">
                 <tr>
                    <th class="ps-3 border-start-0 border-top-0" style="background-color: #f8f9fa; width: 40px;"><input class="form-check-input" type="checkbox" id="checkAllItems" checked></th>
                    <th class="border-top-0 text-dark" style="background-color: #f8f9fa;">Item extraído do Arquivo</th>
                    <th class="text-center border-top-0 text-dark" style="background-color: #f8f9fa;">Detecção Sistema</th>
                    <th class="text-end border-top-0 text-dark" style="background-color: #f8f9fa;">Adição</th>
                    <th class="text-end border-top-0 pe-3 text-dark" style="background-color: #f8f9fa;">Valores Acertados</th>
                 </tr>
             </thead>
             <tbody>${rows}</tbody>
          </table>
        </div>
      `;
    };

    btnProcessar.addEventListener("click", async () => {
        if (!currentFile && !inputUrl.value.trim()) {
            if (window.ui) ui.showToast("Selecione um arquivo ou informe uma URL", "warning");
            return;
        }

        btnProcessar.disabled = true;
        btnProcessar.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Baixando XML...`;

        try {
            let fileToProcess = currentFile;

            if (!fileToProcess && inputUrl.value.trim()) {
                const url = inputUrl.value.trim();
                btnProcessar.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Baixando XML...`;

                try {
                    let xmlContent;
                    try {
                        xmlContent = await fetch(url);
                        if (!xmlContent.ok) {
                            throw new Error(`Falha ao baixar XML: ${xmlContent.status}`);
                        }
                        xmlContent = await xmlContent.text();
                    } catch {
                        const resp = await window.api.downloadXml(url);
                        xmlContent = await resp.text();
                    }

                    fileToProcess = new File(
                        [new Blob([xmlContent], { type: "application/xml" })],
                        `xml_${Date.now()}.xml`,
                        { type: "application/xml" }
                    );
                } catch (fetchError) {
                    throw new Error(`Não foi possível baixar o XML: ${fetchError.message}`);
                }
            }

            btnProcessar.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Analisando...`;

            const resp = await window.api.previewXml(fileToProcess);
            currentAnalysis = resp;

            // Render Meta
            document.getElementById("notaResumoCard").style.display = "flex";
            document.getElementById("notaChaveAcesso").textContent = resp.nota.chave_acesso;
            document.getElementById("notaNumeroSerie").textContent = `Nº ${resp.nota.numero_nota} - Scr. ${resp.nota.serie}`;
            document.getElementById("notaFornecedor").textContent = resp.nota.fornecedor_nome;
            document.getElementById("notaCnpj").textContent = resp.nota.fornecedor_cnpj;

            if (resp.nota.data_emissao) {
                const dparts = resp.nota.data_emissao.split("-");
                document.getElementById("notaEmissao").textContent = dparts.length === 3 ? `${dparts[2]}/${dparts[1]}/${dparts[0]}` : resp.nota.data_emissao;
            }

            document.getElementById("notaValorTotal").textContent = `R$ ${resp.nota.valor_total.toFixed(2)}`;

            // Render items
            document.getElementById("produtosTableContainer").innerHTML = generateTable(resp.produtos);
            btnConfirmar.classList.remove("d-none");

            // CheckAll Logic
            const checkAll = document.getElementById("checkAllItems");
            if (checkAll) {
                checkAll.addEventListener("change", (e) => {
                    document.querySelectorAll(".item-check").forEach(cb => cb.checked = e.target.checked);
                });
            }

            if (window.ui) ui.showToast("XML processado com sucesso. Verifique os dados e confirme a importação.", "success");

        } catch (err) {
            if (window.ui) {
                ui.showToast(ui.getErrorMessage(err), "danger");
                ui.renderInlineError(document.getElementById("produtosTableContainer"), {
                    title: "Falha ao analisar o XML",
                    message: "O arquivo não pôde ser processado neste momento.",
                    details: ui.getErrorMessage(err),
                    actionLabel: "Tentar novamente",
                    action: "document.getElementById('btnProcessarXml').click()"
                });
            }
        } finally {
            btnProcessar.innerHTML = `<i class="bi bi-gear me-2"></i> Processar Novamente`;
            btnProcessar.disabled = false;
        }
    });

    btnConfirmar.addEventListener("click", async () => {
        if (!currentAnalysis) return;

        const checks = document.querySelectorAll(".item-check");
        const selectedIndexes = Array.from(checks).filter(c => c.checked).map(c => parseInt(c.getAttribute("data-idx")));

        if (selectedIndexes.length === 0) {
            if (window.ui) ui.showToast("Selecione ao menos um produto para importar", "warning");
            return;
        }

        const payload = {
            nota: currentAnalysis.nota,
            produtos: selectedIndexes.map(idx => currentAnalysis.produtos[idx])
        };

        btnConfirmar.disabled = true;
        const originalText = btnConfirmar.innerHTML;
        btnConfirmar.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Salvando...`;

        try {
            const resp = await window.api.confirmarImportacaoXml(payload);
            if (window.ui) ui.showToast(resp.message || `NF-e indexada com sucesso! ${resp.produtos_processados} itens afetados na Base.`, "success");

            setTimeout(() => {
                window.location.hash = "#/produtos";
            }, 1500);

        } catch (err) {
            if (window.ui) ui.showToast("Falha na gravação: " + ui.getErrorMessage(err), "danger");
            btnConfirmar.disabled = false;
            btnConfirmar.innerHTML = originalText;
        }
    });
};
