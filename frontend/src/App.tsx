import { useEffect, useState } from 'react'
import { api } from './services/api'
import './App.css'

type HealthCheckResult = {
  status: string
  database: string
}

function App() {
  const [health, setHealth] = useState<HealthCheckResult | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    api
      .get<HealthCheckResult>('/api/health/')
      .then((response) => setHealth(response.data))
      .catch(() => setFailed(true))
  }, [])

  return (
    <>
      <h1>Fire Conference</h1>
      <p>
        {!health && !failed && 'Checking backend status...'}
        {health && `Backend: ${health.status}, database: ${health.database}`}
        {failed && 'Backend unreachable'}
      </p>
    </>
  )
}

export default App
