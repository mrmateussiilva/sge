import { useEffect, useRef, useState } from 'react'
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode'
import { Camera, RefreshCw, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface BarcodeScannerModalProps {
  isOpen: boolean
  onClose: () => void
  onScan: (decodedText: string) => void
  title?: string
}

export function BarcodeScannerModal({
  isOpen,
  onClose,
  onScan,
  title = 'Escanear Código de Barras / QR Code',
}: BarcodeScannerModalProps) {
  const [cameras, setCameras] = useState<{ id: string; label: string }[]>([])
  const [selectedCamera, setSelectedCamera] = useState<string>('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const regionId = 'html5-barcode-scanner-viewport'

  useEffect(() => {
    if (!isOpen) {
      stopScanner()
      setErrorMessage(null)
      return
    }

    let isMounted = true

    Html5Qrcode.getCameras()
      .then((devices) => {
        if (!isMounted) return
        if (devices && devices.length > 0) {
          setCameras(devices)
          // Preferir câmera traseira (environment) se disponível
          const backCamera = devices.find(
            (d) =>
              d.label.toLowerCase().includes('back') ||
              d.label.toLowerCase().includes('traseira') ||
              d.label.toLowerCase().includes('environment')
          )
          setSelectedCamera(backCamera ? backCamera.id : devices[0].id)
        } else {
          setErrorMessage('Nenhuma câmera encontrada no dispositivo.')
        }
      })
      .catch((err) => {
        if (!isMounted) return
        setErrorMessage('Permissão para acessar a câmera foi negada ou não disponível.')
        console.error('Erro ao listar câmeras:', err)
      })

    return () => {
      isMounted = false
      stopScanner()
    }
  }, [isOpen])

  useEffect(() => {
    if (isOpen && selectedCamera) {
      startScanner(selectedCamera)
    }
    return () => {
      stopScanner()
    }
  }, [isOpen, selectedCamera])

  async function stopScanner() {
    if (scannerRef.current) {
      try {
        if (scannerRef.current.isScanning) {
          await scannerRef.current.stop()
        }
        await scannerRef.current.clear()
      } catch (e) {
        console.warn('Erro ao parar scanner:', e)
      } finally {
        scannerRef.current = null
      }
    }
  }

  async function startScanner(cameraId: string) {
    await stopScanner()
    setIsStarting(true)
    setErrorMessage(null)

    try {
      const scanner = new Html5Qrcode(regionId, {
        formatsToSupport: [
          Html5QrcodeSupportedFormats.QR_CODE,
          Html5QrcodeSupportedFormats.EAN_13,
          Html5QrcodeSupportedFormats.EAN_8,
          Html5QrcodeSupportedFormats.CODE_128,
          Html5QrcodeSupportedFormats.CODE_39,
          Html5QrcodeSupportedFormats.UPC_A,
          Html5QrcodeSupportedFormats.UPC_E,
        ],
        verbose: false,
      })
      scannerRef.current = scanner

      await scanner.start(
        cameraId,
        {
          fps: 10,
          qrbox: { width: 250, height: 250 },
          aspectRatio: 1.0,
        },
        (decodedText) => {
          onScan(decodedText.trim())
          onClose()
        },
        () => {
          // Erro de frame não detectado (ignorado por padrão para não poluir console)
        }
      )
    } catch (err: any) {
      console.error('Erro ao iniciar câmera:', err)
      setErrorMessage(err?.message || 'Falha ao iniciar vídeo da câmera.')
    } finally {
      setIsStarting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs animate-in fade-in-0">
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-md overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/40">
          <div className="flex items-center gap-2 font-semibold text-sm">
            <Camera className="w-4 h-4 text-primary" />
            <span>{title}</span>
          </div>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
            ✕
          </Button>
        </div>

        <div className="p-4 flex flex-col items-center">
          <div className="w-full max-w-[320px] aspect-square bg-muted/30 rounded-lg overflow-hidden border border-border relative flex items-center justify-center">
            <div id={regionId} className="w-full h-full" />
            {isStarting && (
              <div className="absolute inset-0 bg-background/70 flex items-center justify-center text-xs text-muted-foreground gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Iniciando câmera...</span>
              </div>
            )}
          </div>

          {errorMessage && (
            <div className="mt-3 p-2 text-xs rounded bg-destructive/15 text-destructive flex items-center gap-2 w-full">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {cameras.length > 1 && (
            <div className="mt-3 w-full">
              <label className="text-xs text-muted-foreground block mb-1">
                Selecionar Câmera
              </label>
              <select
                value={selectedCamera}
                onChange={(e) => setSelectedCamera(e.target.value)}
                className="w-full text-xs h-8 px-2 rounded-md border border-input bg-background"
              >
                {cameras.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label || `Câmera ${c.id}`}
                  </option>
                ))}
              </select>
            </div>
          )}

          <p className="text-xs text-muted-foreground mt-3 text-center">
            Aponte a câmera para o QR Code ou código de barras da etiqueta para selecionar o insumo automaticamente.
          </p>
        </div>

        <div className="px-4 py-3 border-t border-border bg-muted/20 flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </div>
    </div>
  )
}
