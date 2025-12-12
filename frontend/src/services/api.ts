import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
    timeout: 30000,
})

// 请求拦截器：添加 token
api.interceptors.request.use((config) => {
    const token = useAuthStore.getState().token
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// 响应拦截器：处理错误
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            useAuthStore.getState().logout()
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)

// ========== Auth API ==========

export const authApi = {
    login: (username: string, password: string) =>
        api.post('/auth/login', { username, password }),

    register: (data: {
        username: string
        email: string
        password: string
        full_name?: string
        role?: string
    }) => api.post('/auth/register', data),

    getMe: () => api.get('/auth/me'),
}

// ========== Requirements API ==========

export const requirementsApi = {
    list: (params?: { status?: string; skip?: number; limit?: number }) =>
        api.get('/requirements', { params }),

    get: (id: number) => api.get(`/requirements/${id}`),

    create: (data: {
        title: string
        requirement_type?: string
        dimensions?: string
        deadline?: string
        copywriting?: string
        reference_images?: string[]
        additional_notes?: string
        designer_id?: number
    }) => api.post('/requirements', data),

    update: (id: number, data: Record<string, unknown>) =>
        api.patch(`/requirements/${id}`, data),
}

// ========== Tasks API ==========

export const tasksApi = {
    start: (id: number) => api.post(`/tasks/${id}/start`),
    submitReview: (id: number) => api.post(`/tasks/${id}/submit-review`),
    requestRevision: (id: number) => api.post(`/tasks/${id}/request-revision`),
    complete: (id: number) => api.post(`/tasks/${id}/complete`),
    getTimeLogs: (id: number) => api.get(`/tasks/${id}/time-logs`),
}

// ========== Reports API ==========

export const reportsApi = {
    getDesignerStats: (startDate: string, endDate: string, designerId?: number) =>
        api.get('/reports/designer-stats', {
            params: { start_date: startDate, end_date: endDate, designer_id: designerId },
        }),

    exportExcel: (startDate: string, endDate: string) =>
        api.get('/reports/export-excel', {
            params: { start_date: startDate, end_date: endDate },
            responseType: 'blob',
        }),
}

// ========== Admin API ==========

export const adminApi = {
    getDesigners: () => api.get('/admin/designers'),
    getMyDesigner: () => api.get('/admin/my-designer'),
}

export default api
