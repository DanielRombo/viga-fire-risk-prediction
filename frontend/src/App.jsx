import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import DetalheRegiao from './pages/DetalheRegiao.jsx'
import './App.css'

function App() {
  const [darkMode, setDarkMode] = useState(false)

  const toggleDark = () => {
    const novo = !darkMode
    setDarkMode(novo)
    document.documentElement.setAttribute('data-theme', novo ? 'dark' : 'light')
  }

  return (
    <Routes>
      <Route path="/" element={<Dashboard darkMode={darkMode} onToggleDark={toggleDark} />} />
      <Route path="/regiao/:id" element={<DetalheRegiao darkMode={darkMode} onToggleDark={toggleDark} />} />
    </Routes>
  )
}

export default App