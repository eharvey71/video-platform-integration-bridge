import type { ReactNode } from 'react'

export function PageHead({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="page-head">
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </div>
  )
}
