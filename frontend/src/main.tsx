import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { CorpsThemeProvider } from './contexts/CorpsThemeContext'
import { ModeProvider } from './contexts/ModeContext'
import { router } from './router'
import './index.css'
import './App.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CorpsThemeProvider>
      <ModeProvider>
        <RouterProvider router={router} />
      </ModeProvider>
    </CorpsThemeProvider>
  </StrictMode>,
)
