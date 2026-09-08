import { useState } from 'react'

import { useSession } from '../auth/SessionProvider'
import { PageHead } from '../components/PageHead'
import { Card, Empty } from '../components/ui'

export function ApiDocs() {
  const { session } = useSession()
  const features = session?.features ?? { kaltura: false, canvas: false, zoom: false }

  const available = [
    features.kaltura && { key: 'kaltura', label: 'Kaltura', url: '/api/ui/' },
    features.zoom && { key: 'zoom', label: 'Zoom', url: '/zoomapi/ui/' },
  ].filter(Boolean) as { key: string; label: string; url: string }[]

  const [active, setActive] = useState(available[0]?.key ?? '')
  const current = available.find((a) => a.key === active) ?? available[0]

  if (!current) {
    return (
      <>
        <PageHead title="API documentation" />
        <Card>
          <Empty title="No API is enabled">
            Enable the Kaltura or Zoom proxy in Settings, then restart the app.
          </Empty>
        </Card>
      </>
    )
  }

  return (
    <>
      <PageHead title="API documentation">
        The live Swagger UI for each enabled vendor spec.
      </PageHead>

      {available.length > 1 && (
        <div className="inline" style={{ marginBottom: 14 }}>
          {available.map((a) => (
            <button
              key={a.key}
              className={`btn btn-sm ${a.key === current.key ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setActive(a.key)}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}

      <iframe className="docs-frame" src={current.url} title={`${current.label} API documentation`} />
    </>
  )
}
