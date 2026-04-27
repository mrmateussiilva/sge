import xml.etree.ElementTree as ET
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import auth
from database import get_db
from models import Movimentacao, NotaImportada, Produto
from schemas import ConfirmarImportacaoPayload, NotaMeta, PreviewXmlResponse, XmlProduto

router = APIRouter(prefix="/importacao/xml", tags=["Importacao XML"])

def get_ns(root, tag):
    if "}" in root.tag:
        return f"{{{root.tag.split('}')[0].strip('{')}}}{tag}"
    return tag


@router.post("/download")
async def download_xml(
    url: str = Query(..., description="URL do arquivo XML para download"),
    usuario = Depends(auth.get_current_user)
):
    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Dependencia de download XML indisponivel no servidor.",
        ) from exc

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)

        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Não foi possível baixar o XML. Status: {response.status_code}"
            )

        content = response.content
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="O arquivo baixado está vazio.")

        if not response.headers.get("content-type", "").startswith("application/xml") and \
           not response.headers.get("content-type", "").startswith("text/xml") and \
           not url.lower().endswith(".xml"):
            raise HTTPException(
                status_code=400,
                detail="O arquivo retornado não parece ser um XML válido."
            )

        return Response(
            content=content,
            media_type="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="xml_download.xml"',
                "X-Original-URL": url
            }
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Tempo limite esgotado ao baixar o XML.")
    except httpx.RequestError:
        raise HTTPException(status_code=400, detail="Não foi possível conectar à URL fornecida.")


@router.post("/preview", response_model=PreviewXmlResponse)
async def preview_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario = Depends(auth.get_current_user)
):
    if not file.filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="O arquivo deve ser do formato XML.")

    content = await file.read()
    try:
        root = ET.fromstring(content)
    except Exception:
        raise HTTPException(status_code=400, detail="XML inválido ou malformado.")

    nfe = root.find(get_ns(root, "NFe"))
    if nfe is None:
        nfe = root

    infNFe = nfe.find(get_ns(root, "infNFe"))
    if infNFe is None:
        raise HTTPException(status_code=400, detail="Tag infNFe não encontrada. XML não é uma NF-e válida.")

    chave_acesso = infNFe.attrib.get("Id", "").replace("NFe", "")
    if not chave_acesso:
        raise HTTPException(status_code=400, detail="Chave de acesso não encontrada no XML.")

    if db.query(NotaImportada).filter(NotaImportada.chave_acesso == chave_acesso).first():
        raise HTTPException(status_code=400, detail="Esta nota já foi importada no sistema.")

    ide = infNFe.find(get_ns(root, "ide"))
    try:
        numero_nota = ide.findtext(get_ns(root, "nNF"), default="")
        serie = ide.findtext(get_ns(root, "serie"), default="")
        data_emissao = ide.findtext(get_ns(root, "dhEmi")) or ide.findtext(get_ns(root, "dEmi"), default="")
    except AttributeError:
        raise HTTPException(status_code=400, detail="Estrutura de dados ide/nNF ausente.")

    emit = infNFe.find(get_ns(root, "emit"))
    try:
        fornecedor_nome = emit.findtext(get_ns(root, "xNome"), default="")
        fornecedor_cnpj = emit.findtext(get_ns(root, "CNPJ"), default="")
    except AttributeError:
        raise HTTPException(status_code=400, detail="Fornecedor (emit/xNome/CNPJ) ausente.")

    total = infNFe.find(get_ns(root, "total"))
    icmsTot = total.find(get_ns(root, "ICMSTot")) if total is not None else None
    valor_total_nota = float(icmsTot.findtext(get_ns(root, "vNF")) if icmsTot is not None else 0.0)

    nota_meta = NotaMeta(
        numero_nota=numero_nota,
        serie=serie,
        chave_acesso=chave_acesso,
        data_emissao=data_emissao.split("T")[0] if "T" in data_emissao else data_emissao,
        fornecedor_nome=fornecedor_nome,
        fornecedor_cnpj=fornecedor_cnpj,
        valor_total=valor_total_nota
    )

    produtos_xml = []
    for det in infNFe.findall(get_ns(root, "det")):
        prod = det.find(get_ns(root, "prod"))
        if prod is None:
            continue
            
        codigo = prod.findtext(get_ns(root, "cProd"), default="")
        descricao = prod.findtext(get_ns(root, "xProd"), default="")
        ncm = prod.findtext(get_ns(root, "NCM"), default="")
        cfop = prod.findtext(get_ns(root, "CFOP"), default="")
        unidade = prod.findtext(get_ns(root, "uCom"), default="")
        
        try:
            quantidade = float(prod.findtext(get_ns(root, "qCom"), default="0"))
            valor_unitario = float(prod.findtext(get_ns(root, "vUnCom"), default="0"))
            valor_total = float(prod.findtext(get_ns(root, "vProd"), default="0"))
        except ValueError:
            quantidade = valor_unitario = valor_total = 0.0

        exists = db.query(Produto).filter(Produto.sku == codigo).first()
        status = "existente" if exists else "novo"

        produtos_xml.append(XmlProduto(
            codigo=codigo,
            descricao=descricao,
            ncm=ncm,
            cfop=cfop,
            unidade=unidade,
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            valor_total=valor_total,
            status=status
        ))

    return PreviewXmlResponse(nota=nota_meta, produtos=produtos_xml)

@router.post("/confirmar")
def confirmar_importacao(
    payload: ConfirmarImportacaoPayload, 
    db: Session = Depends(get_db),
    usuario = Depends(auth.get_current_user)
):
    if db.query(NotaImportada).filter(NotaImportada.chave_acesso == payload.nota.chave_acesso).first():
        raise HTTPException(status_code=400, detail="Esta nota já foi importada.")

    for item in payload.produtos:
        produto = db.query(Produto).filter(Produto.sku == item.codigo).first()
        if not produto:
            produto = Produto(
                nome=item.descricao,
                sku=item.codigo,
                categoria=f"NCM {item.ncm}" if item.ncm else "Importado NF",
                unidade=item.unidade,
                custo=Decimal(str(item.valor_unitario)),
                preco=Decimal(str(item.valor_unitario)) * Decimal("1.3"),
                estoque_atual=0,
                estoque_minimo=0
            )
            db.add(produto)
            db.flush()

        produto.estoque_atual += int(item.quantidade)
        
        mov = Movimentacao(
            produto_id=produto.id,
            tipo="entrada",
            quantidade=int(item.quantidade),
            motivo=f"Importação XML NF-e nº {payload.nota.numero_nota}"
        )
        db.add(mov)
        
    nota_banco = NotaImportada(
        chave_acesso=payload.nota.chave_acesso,
        numero_nota=payload.nota.numero_nota,
        serie=payload.nota.serie,
        fornecedor_nome=payload.nota.fornecedor_nome,
        fornecedor_cnpj=payload.nota.fornecedor_cnpj,
        valor_total=Decimal(str(payload.nota.valor_total)),
        data_emissao=payload.nota.data_emissao
    )
    db.add(nota_banco)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Falha de integridade ao salvar NF-e no bando de dados.")

    return {"message": "Nota importada com sucesso", "produtos_processados": len(payload.produtos)}
