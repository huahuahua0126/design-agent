import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import MainLayout from './components/MainLayout'
import Login from './pages/Login'
import RequirementChat from './pages/RequirementChat'
import TaskBoard from './pages/TaskBoard'
import Reports from './pages/Reports'

function App() {
    const { isAuthenticated } = useAuthStore()

    if (!isAuthenticated) {
        return (
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
        )
    }

    return (
        <Routes>
            <Route path="/" element={<MainLayout />}>
                <Route index element={<Navigate to="/requirements" replace />} />
                <Route path="requirements" element={<RequirementChat />} />
                <Route path="tasks" element={<TaskBoard />} />
                <Route path="reports" element={<Reports />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    )
}

export default App
