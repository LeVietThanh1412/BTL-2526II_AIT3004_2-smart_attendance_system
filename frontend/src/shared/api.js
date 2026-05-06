// =====================================================================
// shared/api.js - Lớp gọi API dùng chung cho toàn dự án
// Tất cả request đều đi qua Nginx Gateway (/api/*)
// =====================================================================

import axios from 'axios'

// Tạo instance axios riêng để cấu hình baseURL & interceptors tập trung
const apiClient = axios.create({
  baseURL: '/api', // Nginx sẽ proxy sang Backend FastAPI
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor: log lỗi tập trung
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API ERROR]', error?.response?.status, error?.message)
    return Promise.reject(error)
  }
)

// ============= ENDPOINTS THỐNG KÊ =============
export const fetchStatistics = async () => {
  const { data } = await apiClient.get('/thong-ke')
  return data
}

// ============= ENDPOINTS HOẠT ĐỘNG =============
export const fetchRecentActivities = async () => {
  const { data } = await apiClient.get('/activities')
  return data
}

// ============= ENDPOINTS THÔNG BÁO =============
export const fetchNotificationCount = async () => {
  const { data } = await apiClient.get('/thong-bao/chua-doc')
  return data
}

// ============= ENDPOINT ĐIỂM DANH (gửi ảnh base64 lên AI) =============
export const submitCheckIn = async (base64Image) => {
  const { data } = await apiClient.post('/diem-danh', { image: base64Image })
  return data
}

// ============= ENDPOINT ĐĂNG KÝ NHÂN VIÊN =============
export const registerEmployee = async (employeeData) => {
  const { data } = await apiClient.post('/nhan-vien', employeeData)
  return data
}

export default apiClient
