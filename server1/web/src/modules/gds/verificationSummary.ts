type Json = Record<string, unknown>

function pick(obj: Json | undefined, ...keys: string[]): unknown {
  if (!obj) return undefined
  for (const k of keys) {
    if (obj[k] !== undefined && obj[k] !== null) return obj[k]
  }
  return undefined
}

export interface VerificationSummary {
  status: string
  verified: string
  method: string
  matched: string
  filesProcessed: string
  notWatermarkable: string
  failed: string
  traceHash: string
  besu: string
}

export function buildVerificationSummary(data: Json): VerificationSummary {
  const nested = (pick(data, 'verification') as Json | undefined) ?? {}
  const besu = pick(data, 'besu_anchor', 'besuAnchor', 'besu')
  let besuText = '—'
  if (besu && typeof besu === 'object') {
    const b = besu as Json
    besuText = String(pick(b, 'onchain', 'on_chain', 'anchored') ?? JSON.stringify(b))
  } else if (besu != null) {
    besuText = String(besu)
  }
  return {
    status: String(pick(data, 'verification_status', 'verificationStatus') ?? '—'),
    verified: String(pick(nested, 'verified') ?? pick(data, 'verified') ?? '—'),
    method: String(pick(nested, 'method', 'processing_method') ?? '—'),
    matched: String(pick(nested, 'matched') ?? '—'),
    filesProcessed: String(
      pick(nested, 'files_processed', 'filesProcessed', 'samples') ?? '—',
    ),
    notWatermarkable: String(pick(nested, 'not_watermarkable', 'notWatermarkable') ?? '—'),
    failed: String(pick(nested, 'failed') ?? '—'),
    traceHash: String(pick(data, 'trace_record_hash', 'traceRecordHash') ?? '—'),
    besu: besuText,
  }
}
