import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { ModeProvider } from './contexts/ModeContext'
import { ErrorBoundary } from './components/ErrorBoundary'
import { router } from './router'
import './index.css'
import './App.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <ModeProvider>
        <RouterProvider router={router} />
      </ModeProvider>
    </ErrorBoundary>
  </StrictMode>,
)
