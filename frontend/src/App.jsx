import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import './App.css'

function App() {
  const [darkMode, setDarkMode] = useState(false)

  const toggleDark = () => {
    const novo = !darkMode
    setDarkMode(novo)
    document.documentElement.setAttribute('data-theme', novo ? 'dark' : 'light')
  }

  return <Dashboard darkMode={darkMode} onToggleDark={toggleDark} />
}

export default App