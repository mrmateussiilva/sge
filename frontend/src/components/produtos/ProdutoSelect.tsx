import { useId, useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useDebounce } from '@/hooks/useDebounce'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { ProdutoItem, ProdutosResponse } from '@/types'

interface ProdutoSelectProps {
  value: ProdutoItem | null
  onChange: (produto: ProdutoItem | null) => void
  enabled: boolean
}

export function ProdutoSelect({ value, onChange, enabled }: ProdutoSelectProps) {
  const id = useId()
  const [busca, setBusca] = useState('')
  const [pagina, setPagina] = useState(1)
  const termo = useDebounce(busca, 350)
  const { data, isFetching, isError, refetch } = useQuery({
    queryKey: ['produtos-selecao', termo, pagina],
    queryFn: () => {
      const params = new URLSearchParams({ aba: 'TODOS', busca: termo, page: String(pagina), page_size: '25' })
      return api.get<ProdutosResponse>(`/api/v1/produtos/?${params}`)
    },
    enabled,
    placeholderData: keepPreviousData,
  })
  const itens = data?.itens ?? []
  const opcoes = value && !itens.some((produto) => produto.id === value.id) ? [value, ...itens] : itens
  const atualizando = isFetching || busca !== termo

  return (
    <div className="space-y-2 min-w-0" aria-busy={atualizando}>
      <label htmlFor={`${id}-busca`} className="sr-only">Buscar insumo</label>
      <Input
        id={`${id}-busca`}
        placeholder="Buscar insumo por nome ou fornecedor"
        value={busca}
        onChange={(event) => { setBusca(event.target.value); setPagina(1) }}
        className="text-xs"
      />
      <label htmlFor={`${id}-produto`} className="sr-only">Selecionar insumo</label>
      <select
        id={`${id}-produto`}
        value={value?.id ?? ''}
        onChange={(event) => onChange(opcoes.find((produto) => produto.id === Number(event.target.value)) ?? null)}
        className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs"
        disabled={atualizando || isError}
        required
      >
        <option value="">Selecione o insumo...</option>
        {opcoes.map((produto) => (
          <option key={produto.id} value={produto.id}>
            {produto.descricao} (Saldo: {produto.quantidade_formatada})
          </option>
        ))}
      </select>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground" role="status">
        {isError ? (
          <><span>Não foi possível carregar os insumos.</span><Button type="button" size="sm" variant="outline" onClick={() => refetch()}>Tentar novamente</Button></>
        ) : (
          <>
            <span>{atualizando ? 'Buscando...' : `${data?.paginacao.total_itens ?? 0} insumo(s)`}</span>
            {data && data.paginacao.total_paginas > 1 && (
              <>
                <Button type="button" size="sm" variant="outline" disabled={atualizando || !data.paginacao.tem_anterior} onClick={() => setPagina(data.paginacao.pagina_atual - 1)}>Anterior</Button>
                <span>{data.paginacao.pagina_atual}/{data.paginacao.total_paginas}</span>
                <Button type="button" size="sm" variant="outline" disabled={atualizando || !data.paginacao.tem_proxima} onClick={() => setPagina(data.paginacao.pagina_atual + 1)}>Próxima</Button>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}
