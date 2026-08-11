import { useEffect, useState } from 'react'
import { api } from './services/api'
import './App.css'

type HealthStatus = 'loading' | 'healthy' | 'unhealthy'

function App() {
  const [status, setStatus] = useState<HealthStatus>('loading')

  useEffect(() => {
    api
      .get('/api/health/')
      .then(() => setStatus('healthy'))
      .catch(() => setStatus('unhealthy'))
  }, [])

  return (
    <>
      <h1>Fire Conference</h1>
      <p>
        Backend status:{' '}
        {status === 'loading' && 'checking...'}
        {status === 'healthy' && 'healthy ✓'}
        {status === 'unhealthy' && 'unhealthy ✗'}
      </p>
    </>
  )
}

export default App
