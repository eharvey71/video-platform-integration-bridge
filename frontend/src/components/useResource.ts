import { useCallback, useEffect, useState } from 'react'

/** Load-once-with-refresh helper for the read side of each admin screen. */
export function useResource<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      setData(await load())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [load])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { data, setData, error, loading, refresh }
}
