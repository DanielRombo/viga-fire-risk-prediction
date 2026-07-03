import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import DetalheRegiao from './pages/DetalheRegiao'
import Login from './pages/Login'
import RotaProtegida from './components/RotaProtegida'
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
      <Route path="/login" element={<Login />} />
      <Route path="/" element={
        <RotaProtegida>
          <Dashboard darkMode={darkMode} onToggleDark={toggleDark} />
        </RotaProtegida>
      } />
      <Route path="/regiao/:id" element={
        <RotaProtegida>
          <DetalheRegiao darkMode={darkMode} onToggleDark={toggleDark} />
        </RotaProtegida>
      } />
    </Routes>
  )
}

export default App