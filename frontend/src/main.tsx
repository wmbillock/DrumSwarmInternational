import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { ModeProvider } from './contexts/ModeContext'
import { router } from './router'
import './index.css'
import './App.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ModeProvider>
      <RouterProvider router={router} />
    </ModeProvider>
  </StrictMode>,
)
