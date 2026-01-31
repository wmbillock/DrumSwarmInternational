import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { CorpsThemeProvider } from './contexts/CorpsThemeContext'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CorpsThemeProvider>
      <App />
    </CorpsThemeProvider>
  </StrictMode>,
)
