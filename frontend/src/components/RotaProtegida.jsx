import { Navigate } from 'react-router-dom'
import { isAutenticado } from '../services/auth'

function RotaProtegida({ children }) {
    if (!isAutenticado()) {
        return <Navigate to="/login" replace />
    }
    return children
}

export default RotaProtegida