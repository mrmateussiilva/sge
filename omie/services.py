import datetime
import decimal
import urllib.request
import json
import logging
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from estoque.models import Fornecedor, Produto, Movimentacao
from estoque.log_utils import log_acao
from omie.models import OmieConfig, OmieNotaEntrada, OmieNotaEntradaItem, OmieProdutoMapping

logger = logging.getLogger(__name__)


class OmieApiError(Exception):
    pass


def formatar_data_para_omie(data):
    """
    Formatador seguro para converter data do padrão interno para o padrão da API Omie (DD/MM/AAAA).
    Aceita string (YYYY-MM-DD), date ou datetime.
    """
    if not data:
        return ""
    if isinstance(data, (datetime.date, datetime.datetime)):
        return data.strftime("%d/%m/%Y")
    if isinstance(data, str):
        try:
            # Se já estiver em formato DD/MM/AAAA, retorna como está
            if len(data) == 10 and data[2] == "/" and data[5] == "/":
                return data
            # Se estiver em formato YYYY-MM-DD
            dt = datetime.datetime.strptime(data, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            return data
    return str(data)


def parse_data_da_omie(data_str):
    """
    Garante conversão segura de data da API Omie (DD/MM/AAAA) para objeto datetime.date.
    """
    if not data_str:
        return None
    try:
        return datetime.datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        try:
            # Caso venha em formato YYYY-MM-DD
            return datetime.datetime.strptime(data_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None


def omie_call(config: OmieConfig, endpoint: str, call: str, param: dict) -> dict:
    """
    Realiza uma chamada genérica para as APIs RPC da Omie.
    """
    if not config.ativo:
        raise OmieApiError("A configuração do Omie está inativa.")

    app_secret = config.get_app_secret()
    if not config.app_key or not app_secret:
        raise OmieApiError("Credenciais app_key ou app_secret ausentes.")

    # URL base de homologação vs produção
    if config.ambiente == 'HOMOLOGACAO':
        # Nota: Omie utiliza a mesma URL base em alguns endpoints, mas permite mapear as chaves de teste.
        url = endpoint
    else:
        url = endpoint

    payload = {
        "call": call,
        "app_key": config.app_key,
        "app_secret": app_secret,
        "param": [param]
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")

    try:
        # Timeout rígido de 30s conforme especificado
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = response.read()
            decoded_res = res_data.decode('utf-8', errors='replace')
            
            try:
                res_json = json.loads(decoded_res)
            except json.JSONDecodeError as e:
                raise OmieApiError(f"Resposta da API Omie não é um JSON válido: {e}")

            # Verifica erros retornados pela API Omie no formato RPC/SOAP
            if isinstance(res_json, dict):
                faultcode = res_json.get("faultcode")
                faultstring = res_json.get("faultstring")
                if faultcode is not None or faultstring is not None:
                    raise OmieApiError(f"Erro da Omie: {faultstring} (Código: {faultcode})")
            
            return res_json

    except urllib.error.HTTPError as e:
        # Tenta ler o corpo do erro HTTP, pois a Omie costuma retornar erros formatados em JSON no status 500
        err_data = ""
        try:
            err_data = e.read().decode('utf-8', errors='replace')
            err_json = json.loads(err_data)
            faultcode = err_json.get("faultcode")
            faultstring = err_json.get("faultstring")
            if faultcode or faultstring:
                raise OmieApiError(f"Erro da Omie: {faultstring} (Código: {faultcode})")
        except json.JSONDecodeError:
            if err_data:
                raise OmieApiError(f"Erro de servidor da Omie (HTTP {e.code}): {err_data[:300]}")
        except Exception as ex:
            if isinstance(ex, OmieApiError):
                raise ex
        raise OmieApiError(f"Erro de conexão HTTP ao Omie: Código {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        raise OmieApiError(f"Erro de conexão com o Omie: {e.reason}")
    except TimeoutError:
        raise OmieApiError("Tempo limite de conexão com o Omie excedido (30 segundos).")
    except Exception as e:
        if isinstance(e, OmieApiError):
            raise e
        raise OmieApiError(f"Erro inesperado na chamada da API Omie: {e}")


def testar_conexao(config: OmieConfig) -> bool:
    """
    Testa se as credenciais configuradas estão corretas.
    Faz uma chamada de teste no ListarNotaEnt pedindo apenas 1 registro.
    """
    param = {
        "nPagina": 1,
        "nRegistrosPorPagina": 1,
        "cExibirDetalhes": "S",
        "cOrdenarPor": "CODIGO",
    }
    try:
        omie_call(config, "https://app.omie.com.br/api/v1/produtos/notaentrada/", "ListarNotaEnt", param)
        return True
    except Exception as e:
        logger.warning(f"Teste de conexão com a Omie falhou: {e}")
        raise OmieApiError(f"Falha de Conexão: {e}")


def listar_notas_entrada(
    config: OmieConfig,
    data_inicial=None,
    data_final=None,
    pagina=1,
    registros_por_pagina=50,
) -> dict:
    """
    Consulta o endpoint de Notas de Entrada no Omie de forma paginada.

    Filtro de data: usa dtAltDe/dtAltAte (data de alteração) no formato dd/mm/aaaa,
    conforme suportado pelo endpoint ListarNotaEnt da Omie.
    """
    param = {
        "nPagina": pagina,
        "nRegistrosPorPagina": registros_por_pagina,
        "cExibirDetalhes": "S",
        "cOrdenarPor": "CODIGO",
    }

    if data_inicial:
        param["dtAltDe"] = data_inicial.strftime("%d/%m/%Y")
    if data_final:
        param["dtAltAte"] = data_final.strftime("%d/%m/%Y")

    return omie_call(
        config=config,
        endpoint="https://app.omie.com.br/api/v1/produtos/notaentrada/",
        call="ListarNotaEnt",
        param=param,
    )


def normalizar_cnpj(cnpj: str) -> str:
    """Garante CNPJ apenas com dígitos numéricos para buscas."""
    if not cnpj:
        return ""
    return "".join(c for c in str(cnpj) if c.isdigit())


def normalizar_nota_entrada(raw: dict) -> dict:
    """
    Normaliza a estrutura do JSON bruto de uma nota retornada pelo ListarNotaEnt da Omie.

    A Omie retorna a chave 'cabec' (não 'cabecalho') com os campos:
      - nCodNotaEnt: código interno Omie
      - cNumeroNotaEnt: número da nota
      - dPrevisao: data da nota (formato dd/mm/aaaa)
      - nCodCli: código interno do fornecedor/cliente (sem CNPJ direto)
    """
    # Suporta tanto 'cabec' (real) quanto 'cabecalho' (testes/mock)
    cabec = raw.get("cabec") or raw.get("cabecalho") or {}
    fornecedor = raw.get("fornecedor") or {}

    # Datas — campo real é dPrevisao; mocks podem usar dDtEmissao
    d_emissao = (
        parse_data_da_omie(cabec.get("dDtEmissao"))
        or parse_data_da_omie(cabec.get("dPrevisao"))
    )
    d_entrada = (
        parse_data_da_omie(cabec.get("dDtEntrada"))
        or parse_data_da_omie(cabec.get("dDtReg"))
        or d_emissao
    )

    # CNPJ — presente em mocks; na API real vem como nCodCli (código)
    cnpj = normalizar_cnpj(
        fornecedor.get("cCNPJ")
        or fornecedor.get("cCNPJCPF")
        or ""
    )

    # Chave NFe — se vazia, salva como None para evitar erros de restrição UNIQUE no banco
    chave_nfe_raw = str(cabec.get("cChaveNFe") or "").strip().replace(" ", "")
    chave_nfe = chave_nfe_raw if chave_nfe_raw else None

    # Código interno Omie — campo real é nCodNotaEnt; mocks usam nIdReceb
    omie_codigo = str(
        cabec.get("nCodNotaEnt")
        or cabec.get("nIdReceb")
        or ""
    )

    # Número da nota — campo real é cNumeroNotaEnt; mocks usam nNumNota
    numero_nf = str(
        cabec.get("cNumeroNotaEnt")
        or cabec.get("nNumNota")
        or ""
    )

    # Código do cliente/fornecedor Omie (para lookup futuro)
    cod_cli = str(cabec.get("nCodCli") or "")

    return {
        "omie_codigo_nota": omie_codigo,
        "omie_codigo_integracao": str(cabec.get("cCodInt") or ""),
        "chave_nfe": chave_nfe,
        "numero_nf": numero_nf,
        "serie": str(cabec.get("cSerieNota") or cabec.get("cSerie") or ""),
        "fornecedor_nome": str(fornecedor.get("cNome") or "").strip(),
        "fornecedor_cnpj": cnpj,
        "omie_cod_cliente": cod_cli,
        "data_emissao": d_emissao,
        "data_entrada": d_entrada,
        "valor_total": decimal.Decimal(str(
            cabec.get("nValNota")
            or cabec.get("nValTotal")
            or 0.0
        )),
    }


def normalizar_item_nota(raw_item: dict) -> dict:
    """
    Normaliza a estrutura do JSON de produto/item da Omie para nosso dicionário.
    A Omie geralmente retorna os produtos em um formato como {"prod_det": {...}}.
    """
    prod_det = raw_item.get("prod_det", {})
    
    # Tratando valores decimais
    qtd = decimal.Decimal(str(prod_det.get("nQtde") or 0.0))
    val_unit = decimal.Decimal(str(prod_det.get("nValUnit") or 0.0))
    val_tot = decimal.Decimal(str(prod_det.get("nValTotal") or 0.0))

    return {
        "sequencia": int(prod_det.get("nSequencia") or 1),
        "codigo_produto_omie": str(prod_det.get("nIdProd") or prod_det.get("cCodProd") or ""),
        "codigo_produto_fornecedor": str(prod_det.get("cCodProdFor") or prod_det.get("cCodProdFornecedor") or ""),
        "descricao": str(prod_det.get("cDescricao") or "").strip(),
        "ncm": str(prod_det.get("cNCM") or "").strip(),
        "cfop": str(prod_det.get("cCFOP") or "").strip(),
        "unidade_nota": str(prod_det.get("cUnidade") or "").strip().upper(),
        "quantidade_nota": qtd,
        "valor_unitario": val_unit,
        "valor_total": val_tot,
    }


def sincronizar_notas_entrada(config: OmieConfig, data_inicial=None, data_final=None, usuario=None) -> dict:
    """
    Executa a sincronização com a Omie e atualiza as notas de entrada locais.
    """
    resumo = {
        "criadas": 0,
        "atualizadas": 0,
        "erros": 0,
        "erros_detalhes": []
    }
    
    if not config.ativo:
        raise OmieApiError("Configuração Omie inativa.")

    pagina = 1
    total_de_paginas = 1

    while pagina <= total_de_paginas:
        try:
            resposta = listar_notas_entrada(
                config,
                data_inicial=data_inicial,
                data_final=data_final,
                pagina=pagina,
                registros_por_pagina=50
            )
        except OmieApiError as e:
            err_str = str(e)
            # Código 5113: "Não existem registros para a página" = resultado vazio, não é erro
            if "5113" in err_str:
                logger.info(f"Omie não retornou registros na página {pagina} (resultado vazio).")
                break
            # Erro na primeira página = falha crítica, propaga para o command
            if pagina == 1:
                raise
            msg = f"Falha ao listar notas da Omie na página {pagina}: {e}"
            logger.error(msg)
            resumo["erros"] += 1
            resumo["erros_detalhes"].append(msg)
            break
        except Exception as e:
            if pagina == 1:
                raise
            msg = f"Erro inesperado ao listar página {pagina}: {e}"
            logger.error(msg)
            resumo["erros"] += 1
            resumo["erros_detalhes"].append(msg)
            break

        # Tenta ler paginação — Omie usa nTotalPaginas na resposta real
        try:
            total_de_paginas = int(
                resposta.get("nTotalPaginas")
                or resposta.get("nTotPaginas")
                or resposta.get("total_de_paginas")
                or 1
            )
        except (ValueError, TypeError):
            total_de_paginas = 1

        # Chave real da Omie é 'notas'; mocks usam 'nota_fiscal_entrada_completa'
        notas_list = (
            resposta.get("notas")
            or resposta.get("nota_fiscal_entrada_completa")
            or resposta.get("notas_cadastro")
            or resposta.get("dados_cadastro")
            or []
        )
        if not isinstance(notas_list, list):
            notas_list = [notas_list]

        if not notas_list:
            break

        for raw_nota in notas_list:
            if not raw_nota:
                continue
            
            try:
                # Normaliza dados de cabeçalho
                nota_dados = normalizar_nota_entrada(raw_nota)
                
                # Se não houver identificador chave, pula
                chave_nfe = nota_dados.get("chave_nfe")
                omie_codigo_nota = nota_dados.get("omie_codigo_nota")
                
                if not chave_nfe and not omie_codigo_nota:
                    continue

                # Busca fornecedor existente no banco local pelo CNPJ
                fornecedor_obj = None
                cnpj_normalizado = nota_dados["fornecedor_cnpj"]
                if cnpj_normalizado:
                    # Busca fornecedores tentando casar CNPJ numérico puro
                    for f in Fornecedor.objects.all():
                        if normalizar_cnpj(f.cnpj) == cnpj_normalizado:
                            fornecedor_obj = f
                            break

                # Tenta localizar nota existente
                nota_obj = None
                if chave_nfe:
                    nota_obj = OmieNotaEntrada.objects.filter(chave_nfe=chave_nfe).first()
                if not nota_obj and omie_codigo_nota:
                    nota_obj = OmieNotaEntrada.objects.filter(omie_codigo_nota=omie_codigo_nota).first()

                # Se a nota já foi importada ou aprovada, não sobrescrevemos
                if nota_obj and nota_obj.status in ['IMPORTADA', 'APROVADA']:
                    continue

                is_new = nota_obj is None
                if is_new:
                    nota_obj = OmieNotaEntrada()

                # Atualiza campos
                nota_obj.chave_nfe = chave_nfe
                nota_obj.omie_codigo_nota = omie_codigo_nota
                nota_obj.omie_codigo_integracao = nota_dados["omie_codigo_integracao"]
                nota_obj.numero_nf = nota_dados["numero_nf"]
                nota_obj.serie = nota_dados["serie"]
                nota_obj.fornecedor_nome = nota_dados["fornecedor_nome"]
                nota_obj.fornecedor_cnpj = cnpj_normalizado
                nota_obj.fornecedor = fornecedor_obj
                nota_obj.data_emissao = nota_dados["data_emissao"]
                nota_obj.data_entrada = nota_dados["data_entrada"]
                nota_obj.valor_total = nota_dados["valor_total"]
                nota_obj.raw_json = raw_nota
                
                # Reseta erro caso estivesse com erro
                if nota_obj.status == 'ERRO':
                    nota_obj.status = 'PENDENTE'
                    nota_obj.erro = ""
                
                nota_obj.save()

                if is_new:
                    resumo["criadas"] += 1
                else:
                    resumo["atualizadas"] += 1

                # Sincroniza os itens da nota
                raw_produtos = raw_nota.get("produtos") or raw_nota.get("det") or []
                if not isinstance(raw_produtos, list):
                    raw_produtos = [raw_produtos]

                itens_id_existentes = set(nota_obj.itens.values_list('id', flat=True))
                itens_processados = []

                for raw_prod in raw_produtos:
                    if not raw_prod:
                        continue
                    
                    item_dados = normalizar_item_nota(raw_prod)
                    seq = item_dados["sequencia"]
                    
                    # Localiza item existente na nota pelo sequencial
                    item_obj = nota_obj.itens.filter(sequencia=seq).first()
                    if not item_obj:
                        item_obj = OmieNotaEntradaItem(
                            nota=nota_obj,
                            sequencia=seq
                        )
                    
                    # Atualiza os dados brutos e da nota
                    item_obj.codigo_produto_omie = item_dados["codigo_produto_omie"]
                    item_obj.codigo_produto_fornecedor = item_dados["codigo_produto_fornecedor"]
                    item_obj.descricao = item_dados["descricao"]
                    item_obj.ncm = item_dados["ncm"]
                    item_obj.cfop = item_dados["cfop"]
                    item_obj.unidade_nota = item_dados["unidade_nota"]
                    item_obj.quantidade_nota = item_dados["quantidade_nota"]
                    item_obj.valor_unitario = item_dados["valor_unitario"]
                    item_obj.valor_total = item_dados["valor_total"]
                    item_obj.raw_json = raw_prod

                    # Se já estiver importado, mantém
                    if item_obj.status == 'IMPORTADO':
                        item_obj.save()
                        itens_processados.append(item_obj.id)
                        continue

                    # Tentativa de mapeamento automático do Produto
                    produto_vinculado = None
                    fator_conversao = decimal.Decimal("1.000000")
                    
                    # Busca mapping por CNPJ fornecedor + dados do produto
                    mapping = None
                    if cnpj_normalizado:
                        # 1. Por codigo_produto_omie
                        if item_obj.codigo_produto_omie:
                            mapping = OmieProdutoMapping.objects.filter(
                                fornecedor_cnpj=cnpj_normalizado,
                                codigo_produto_omie=item_obj.codigo_produto_omie,
                                ativo=True
                            ).first()
                        
                        # 2. Por codigo_produto_fornecedor
                        if not mapping and item_obj.codigo_produto_fornecedor:
                            mapping = OmieProdutoMapping.objects.filter(
                                fornecedor_cnpj=cnpj_normalizado,
                                codigo_produto_fornecedor=item_obj.codigo_produto_fornecedor,
                                ativo=True
                            ).first()

                    if mapping:
                        produto_vinculado = mapping.produto
                        fator_conversao = mapping.fator_conversao_para_base

                    # Se encontrou mapping automático
                    if produto_vinculado:
                        item_obj.produto = produto_vinculado
                        item_obj.quantidade_convertida = item_obj.quantidade_nota * fator_conversao
                        item_obj.unidade_convertida = produto_vinculado.unidade_medida
                        item_obj.status = 'VINCULADO'
                    else:
                        # Se já existia um vínculo manual anterior, preservamos
                        if item_obj.produto:
                            # Re-calcula caso a quantidade da nota tenha mudado
                            if item_obj.quantidade_convertida is None:
                                item_obj.quantidade_convertida = item_obj.quantidade_nota
                            item_obj.status = 'VINCULADO'
                        else:
                            item_obj.status = 'PENDENTE'

                    item_obj.save()
                    itens_processados.append(item_obj.id)

                # Remove itens que estavam no banco mas sumiram da nota na sincronização
                excluir_ids = itens_id_existentes - set(itens_processados)
                if excluir_ids:
                    nota_obj.itens.filter(id__in=excluir_ids).delete()

            except Exception as e:
                msg_erro = f"Erro ao processar dados da nota individual da Omie: {e}"
                logger.exception(msg_erro)
                resumo["erros"] += 1
                resumo["erros_detalhes"].append(msg_erro)

        pagina += 1

    # Atualiza a última sincronização da configuração
    config.ultima_sincronizacao = timezone.now()
    config.save(update_fields=['ultima_sincronizacao'])

    # Registra no log de auditoria
    if usuario and usuario.is_authenticated:
        log_acao(
            usuario, 'EDITAR',
            f"Sincronização manual executada. Notas Criadas: {resumo['criadas']}, Atualizadas: {resumo['atualizadas']}, Erros: {resumo['erros']}",
            'OmieConfig', config.id
        )

    return resumo


def aprovar_nota_entrada(nota: OmieNotaEntrada, usuario) -> dict:
    """
    Aprova a nota fiscal de entrada gerando movimentações no estoque.
    Todo o fluxo corre dentro de transação atômica.
    """
    if not nota.pode_aprovar():
        raise ValidationError("A nota não está elegível para aprovação. Verifique se todos os itens estão vinculados a produtos e se a nota já foi importada.")

    with transaction.atomic():
        # Lock da nota no banco de dados para evitar concorrência/duplicação
        nota_lock = OmieNotaEntrada.objects.select_for_update().get(pk=nota.pk)
        if nota_lock.status in ['IMPORTADA', 'APROVADA']:
            raise ValidationError("Esta nota já foi processada por outro processo.")

        itens = nota_lock.itens.all()
        movimentacoes_criadas = []

        for item in itens:
            if item.status == 'IGNORADO':
                continue

            # Validações defensivas
            if not item.produto:
                raise ValidationError(f"Item '{item.descricao}' não possui produto associado.")
            if item.movimentacao:
                # Evita duplicar movimentação para o mesmo item
                continue

            qtd_movimento = item.quantidade_para_entrada()
            if qtd_movimento <= 0:
                raise ValidationError(f"Quantidade do item '{item.descricao}' convertida para estoque deve ser maior que zero (atual: {qtd_movimento}).")

            # Cria a movimentação de estoque
            # NOTA: O método save() da Movimentacao já faz o select_for_update() e atualiza a quantidade_base do produto de forma segura
            mov = Movimentacao(
                produto=item.produto,
                usuario=usuario,
                tipo='ENTRADA',
                quantidade=qtd_movimento,
                observacao=f"Entrada via Omie - NF {nota_lock.numero_nf or 'S/N'} - Chave {nota_lock.chave_nfe or 'S/C'}"
            )
            mov.save()

            # Associa a movimentação criada ao item da nota
            item.movimentacao = mov
            item.status = 'IMPORTADO'
            item.save(update_fields=['movimentacao', 'status'])
            
            movimentacoes_criadas.append(mov)

            # Opcional: cria/atualiza o mapping de produto automaticamente com base no vínculo manual atual
            # Se não existir mapping para CNPJ + código omie/fornecedor, vamos criar para agilizar futuras importações
            if nota_lock.fornecedor_cnpj:
                fator = decimal.Decimal("1.000000")
                if item.quantidade_convertida is not None and item.quantidade_nota > 0:
                    fator = item.quantidade_convertida / item.quantidade_nota

                # Garante que não crie chaves duplicadas
                OmieProdutoMapping.objects.get_or_create(
                    fornecedor_cnpj=nota_lock.fornecedor_cnpj,
                    codigo_produto_omie=item.codigo_produto_omie,
                    codigo_produto_fornecedor=item.codigo_produto_fornecedor,
                    defaults={
                        'fornecedor': nota_lock.fornecedor,
                        'descricao_fornecedor': item.descricao,
                        'produto': item.produto,
                        'unidade_nota': item.unidade_nota,
                        'fator_conversao_para_base': fator,
                        'ativo': True
                    }
                )

        # Atualiza o cabeçalho da nota
        nota_lock.status = 'IMPORTADA'
        nota_lock.aprovado_por = usuario
        nota_lock.aprovado_em = timezone.now()
        nota_lock.erro = ""
        nota_lock.save(update_fields=['status', 'aprovado_por', 'aprovado_em', 'erro'])

        # Registra a ação na auditoria
        log_acao(
            usuario, 'RECEBER',
            f"Recebimento de Nota Omie executado. NF {nota_lock.numero_nf}, {len(movimentacoes_criadas)} item(ns) importados.",
            'OmieNotaEntrada', nota_lock.id
        )

        return {
            "sucesso": True,
            "itens_importados": len(movimentacoes_criadas)
        }
