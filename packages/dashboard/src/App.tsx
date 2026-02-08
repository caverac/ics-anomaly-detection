import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from '@/components/Layout'
import { Alerts } from '@/routes/Alerts'
import { Dashboard } from '@/routes/Dashboard'
import { Incidents } from '@/routes/Incidents'
import { Network } from '@/routes/Network'
import { Settings } from '@/routes/Settings'

export const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/network" element={<Network />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        {/* Redirect root to dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
