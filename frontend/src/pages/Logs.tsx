import { useCallback, useMemo, useState } from 'react'

import { api } from '../api/client'
import { PageHead } from '../components/PageHead'
import { Alert, Card, Empty, Loading } from '../components/ui'
import { useResource } from '../components/useResource'

const LIMITS = [200, 500, 2000, 5000]

function lineClass(line: string) {
  if (/ - (ERROR|CRITICAL) - /.test(line)) return 'log-line is-error'
  if (/ - WARNING - /.test(line)) return 'log-line is-warn'
  return 'log-line'
}

export function Logs() {
  const [limit, setLimit] = useState(500)
  const [filter, setFilter] = useState('')

  const load = useCallback(() => api.logs.get(limit), [limit])
  const { data, error, loading, refresh } = useResource(load)

  const lines = useMemo(() => {
    const all = data?.lines ?? []
    if (!filter.trim()) return all
    const needle = filter.toLowerCase()
    return all.filter((l) => l.toLowerCase().includes(needle))
  }, [data, filter])

  return (
    <>
      <PageHead title="Event log">
        Every proxied request and configuration change, newest first.
      </PageHead>

      {error && <Alert kind="error">{error}</Alert>}

      <Card
        title={`${lines.length.toLocaleString()} line${lines.length === 1 ? '' : 's'}`}
        description={data?.total ? `${data.total.toLocaleString()} in the current log file` : undefined}
        actions={
          <>
            <input
              className="input"
              style={{ width: 190 }}
              placeholder="Filter…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            <select
              className="select"
              style={{ width: 'auto' }}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            >
              {LIMITS.map((n) => (
                <option key={n} value={n}>
                  Last {n.toLocaleString()}
                </option>
              ))}
            </select>
            <button className="btn btn-ghost btn-sm" onClick={() => void refresh()} disabled={loading}>
              Refresh
            </button>
            <a className="btn btn-ghost btn-sm" href="/logs/log" download>
              Download
            </a>
          </>
        }
      >
        {loading ? (
          <Loading label="Reading log" />
        ) : lines.length === 0 ? (
          <Empty title="Nothing to show">
            {filter ? 'No lines match that filter.' : 'The log file is empty.'}
          </Empty>
        ) : (
          <div className="log">
            {lines.map((line, i) => (
              <span key={i} className={lineClass(line)}>
                {line}
              </span>
            ))}
          </div>
        )}
      </Card>
    </>
  )
}
