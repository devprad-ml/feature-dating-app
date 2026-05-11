import { useEffect, useMemo, useState } from 'react'
import { submitMemory, getMemoryState, reactToMemory } from './api.js'

const MIN = 80
const MAX = 1500
const POLL_MS = 2000

function readMemoryIdFromUrl() {
  return new URLSearchParams(window.location.search).get('memory_id')
}

function setMemoryIdInUrl(id) {
  const url = new URL(window.location.href)
  if (id) url.searchParams.set('memory_id', id)
  else url.searchParams.delete('memory_id')
  window.history.replaceState({}, '', url.toString())
}

export default function App() {
  const [handle, setHandle] = useState('you')
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [state, setState] = useState(null)  // { you, echo }
  const [hydrating, setHydrating] = useState(true)

  // On mount, hydrate from URL if present
  useEffect(() => {
    const memId = readMemoryIdFromUrl()
    if (!memId) { setHydrating(false); return }
    getMemoryState(memId)
      .then(setState)
      .catch((e) => setError(e.message))
      .finally(() => setHydrating(false))
  }, [])

  // Poll while we're in a non-final state
  useEffect(() => {
    if (!state?.you?.id || !state?.echo) return
    const echo = state.echo
    const myDone = echo.my_reaction === 'no'
    const bothDone = echo.my_reaction != null && echo.their_reaction != null
    if (myDone || bothDone) return

    const id = setInterval(async () => {
      try {
        const fresh = await getMemoryState(state.you.id)
        setState(fresh)
      } catch (_) {/* silent — next tick will retry */}
    }, POLL_MS)
    return () => clearInterval(id)
  }, [state?.you?.id, state?.echo?.my_reaction, state?.echo?.their_reaction])

  const len = text.length
  const tooShort = len < MIN
  const tooLong = len > MAX
  const valid = !tooShort && !tooLong && handle.trim().length > 0

  const submit = async () => {
    if (!valid || submitting) return
    setSubmitting(true); setError(null)
    try {
      const data = await submitMemory({ authorHandle: handle.trim(), text: text.trim() })
      setState(data)
      setMemoryIdInUrl(data.you.id)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const reset = () => {
    setMemoryIdInUrl(null)
    setState(null)
    setText('')
    setError(null)
  }

  const onReact = async (kind) => {
    if (!state?.you?.id || !state?.echo?.memory?.id) return
    try {
      const fresh = await reactToMemory({
        fromMemoryId: state.you.id,
        toMemoryId: state.echo.memory.id,
        kind,
      })
      setState(fresh)
    } catch (e) { setError(e.message) }
  }

  if (hydrating) {
    return (
      <Shell>
        <div className="spacer" style={{ display: 'flex', alignItems: 'center' }}>
          <div className="spinner" />
        </div>
      </Shell>
    )
  }

  return (
    <Shell>
      {!state && !submitting && (
        <Compose
          handle={handle} setHandle={setHandle}
          text={text} setText={setText}
          len={len} tooShort={tooShort} tooLong={tooLong}
          valid={valid} error={error} onSubmit={submit}
        />
      )}

      {submitting && (
        <div className="spacer" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div className="spinner" />
          <div className="thinking">listening for what your memory reveals…</div>
        </div>
      )}

      {state && !submitting && (
        <Result state={state} error={error} onReact={onReact} onAnother={reset} />
      )}
    </Shell>
  )
}

function Shell({ children }) {
  return (
    <div className="shell">
      <div className="card">
        <div className="card-header">
          <div className="brand">Echoes</div>
          <div className="tagline">memory as match</div>
        </div>
        <div className="card-body">{children}</div>
      </div>
    </div>
  )
}

function Compose({ handle, setHandle, text, setText, len, tooShort, tooLong, valid, error, onSubmit }) {
  return (
    <>
      <h1>Write a memory.</h1>
      <p className="subtitle">
        Anything real from your life. The smaller and more specific, the better.
        We'll show you what it reveals about you — and pair you with someone whose
        memory carries a related lesson.
      </p>

      <label htmlFor="handle">Your handle</label>
      <input
        id="handle"
        className="handle-input"
        value={handle}
        onChange={(e) => setHandle(e.target.value)}
        maxLength={64}
      />

      <label htmlFor="memory">The memory</label>
      <textarea
        id="memory"
        className="memory-input"
        placeholder="A moment you keep returning to. A small one. Three sentences is plenty."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className={`counter ${(tooShort && len > 0) || tooLong ? 'invalid' : ''}`}>
        <span>
          {len === 0
            ? `at least ${MIN} characters`
            : tooShort
              ? `${MIN - len} more to go`
              : tooLong
                ? `${len - MAX} over the limit`
                : `${len} / ${MAX}`}
        </span>
        <span style={{ fontStyle: 'italic' }}>
          this stays anonymous unless someone resonates with it
        </span>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="spacer" />

      <button className="primary-btn" disabled={!valid} onClick={onSubmit}>
        Submit
      </button>
    </>
  )
}

function Result({ state, error, onReact, onAnother }) {
  const { you, echo } = state
  const overlapSet = useMemo(() => {
    if (!echo) return new Set()
    return new Set(echo.overlap_themes.map((t) => t.toLowerCase()))
  }, [echo])

  return (
    <>
      <h1>Here's what your memory revealed.</h1>

      <AnalysisCard mem={you} overlapSet={new Set()} />

      {echo ? (
        <>
          <div className="echo-divider">your echo</div>
          <div className="echo-reason">{echo.resonance_reason}</div>
          <div className="echo-author">— @{echo.memory.author_handle}</div>
          <div className="echo-text">{echo.memory.text}</div>
          <AnalysisCard mem={echo.memory} overlapSet={overlapSet} compact />

          <ReactionPanel echo={echo} onReact={onReact} />
        </>
      ) : (
        <>
          <div className="echo-divider">no echo yet</div>
          <p className="subtitle" style={{ textAlign: 'center' }}>
            You're the first memory in the system. The next person to write will be paired with yours.
          </p>
        </>
      )}

      {error && <div className="error">{error}</div>}

      <div className="spacer" />

      <button className="secondary-btn" onClick={onAnother}>
        Write another memory
      </button>
    </>
  )
}

function ReactionPanel({ echo, onReact }) {
  const handle = echo.memory.author_handle
  const mine = echo.my_reaction
  const theirs = echo.their_reaction

  // 1) undecided — show buttons
  if (mine == null) {
    return (
      <>
        <div className="reaction-prompt">
          Want to keep talking with @{handle}?
          <span className="reaction-hint">
            both of you have to say yes for a chat to open. one-shot decision.
          </span>
        </div>
        <div className="reaction-row">
          <button className="reaction-btn no" onClick={() => onReact('no')}>
            No thanks
          </button>
          <button className="reaction-btn yes" onClick={() => onReact('yes')}>
            Yes, want to match
          </button>
        </div>
      </>
    )
  }

  // 2) mutual yes — match
  if (echo.mutual) {
    return (
      <div className="match-banner">
        <div className="match-banner-title">Mutual echo.</div>
        <div className="match-banner-body">
          You both said yes. <strong>@{handle}</strong> can be reached now —
          start the conversation knowing they already saw what your memory revealed.
        </div>
      </div>
    )
  }

  // 3) I said no
  if (mine === 'no') {
    return (
      <div className="state-banner muted">
        You passed on this one. No match.
      </div>
    )
  }

  // 4) I said yes, waiting on them
  if (mine === 'yes' && theirs == null) {
    return (
      <div className="state-banner waiting">
        <div className="dot-pulse"><span /><span /><span /></div>
        You said yes. Waiting on @{handle}…
      </div>
    )
  }

  // 5) I said yes, they said no
  if (mine === 'yes' && theirs === 'no') {
    return (
      <div className="state-banner muted">
        This one didn't unlock. Sometimes you click, sometimes you don't.
      </div>
    )
  }

  return null
}

function AnalysisCard({ mem, overlapSet, compact = false }) {
  return (
    <div className="analysis">
      {!compact && <p className="analysis-essence">"{mem.one_line_essence}"</p>}

      <div className="analysis-row">
        <div className="k">themes</div>
        <div className="v">
          <div className="theme-chips">
            {mem.themes.map((t) => (
              <span
                key={t}
                className={`theme-chip ${overlapSet.has(t.toLowerCase()) ? 'overlap' : ''}`}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="analysis-row">
        <div className="k">emotion</div>
        <div className="v">{mem.emotional_register}</div>
      </div>

      <div className="analysis-row">
        <div className="k">lesson</div>
        <div className="v lesson">{mem.lesson}</div>
      </div>
    </div>
  )
}
