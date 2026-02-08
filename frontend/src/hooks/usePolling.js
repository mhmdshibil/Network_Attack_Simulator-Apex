import { useEffect, useState } from 'react'

/**
 * Custom hook for polling API endpoints
 * @param {string} url - API endpoint URL
 * @param {number} interval - Polling interval in milliseconds (default: 5000)
 * @returns {object} { data, loading, error, refetch }
 */
export function usePolling(url, interval = 5000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = async () => {
    try {
      setError(null)
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`)
      }

      const result = await response.json()
      setData(result)
      setLoading(false)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  useEffect(() => {
    // Initial fetch
    fetchData()

    // Set up polling
    const pollInterval = setInterval(fetchData, interval)

    // Cleanup
    return () => clearInterval(pollInterval)
  }, [url, interval])

  return { data, loading, error, refetch: fetchData }
}
