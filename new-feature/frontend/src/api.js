const BASE = '/api'

async function jsonOrThrow(res) {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch (_) {}
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json()
}

export async function submitMemory({ authorHandle, text }) {
  const res = await fetch(`${BASE}/memory`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ author_handle: authorHandle, text }),
  })
  return jsonOrThrow(res)
}

export async function getMemoryState(memoryId) {
  const res = await fetch(`${BASE}/memory/${memoryId}`)
  return jsonOrThrow(res)
}

export async function reactToMemory({ fromMemoryId, toMemoryId, kind }) {
  const res = await fetch(`${BASE}/memory/${fromMemoryId}/react`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ to_memory_id: toMemoryId, kind }),
  })
  return jsonOrThrow(res)
}
