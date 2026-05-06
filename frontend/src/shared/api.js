// =====================================================================
// shared/api.js - Lớp gọi API dùng chung cho toàn dự án
// Tất cả request đều đi qua Nginx Gateway (/api/*)
// =====================================================================

import axios from 'axios'

// Tạo instance axios riêng để cấu hình baseURL & interceptors tập trung
const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// Interceptor: log lỗi tập trung
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API ERROR]', error?.response?.status, error?.message)
    return Promise.reject(error)
  }
)

const demoStatistics = {
  total: 50,
  missing: 8,
  onTime: 38,
  late: 4,
}

const demoActivities = [
  { name: 'Trần Thị B', time: '08:15:22', date: '04/05/2026', status: 'Đi muộn', statusColor: 'red' },
  { name: 'Lê Văn C', time: '07:55:10', date: '04/05/2026', status: 'Đúng giờ', statusColor: 'green' },
  { name: 'Phạm Thu D', time: '07:45:00', date: '04/05/2026', status: 'Đúng giờ', statusColor: 'green' },
  { name: 'Hoàng Văn E', time: '07:30:15', date: '04/05/2026', status: 'Đúng giờ', statusColor: 'green' },
]

const demoNotifications = {
  count: 5,
}

// ============= ENDPOINTS THỐNG KÊ =============
export const fetchStatistics = async () => {
  return { ...demoStatistics }
}

// ============= ENDPOINTS HOẠT ĐỘNG =============
export const fetchRecentActivities = async () => {
  return [...demoActivities]
}

// ============= ENDPOINTS THÔNG BÁO =============
export const fetchNotificationCount = async () => {
  return { ...demoNotifications }
}

// ============= ENDPOINT ĐIỂM DANH (gửi ảnh base64 lên AI) =============
export const submitCheckIn = async (base64Image) => {
  const imageSource = base64Image.startsWith('data:')
    ? base64Image
    : `data:image/jpeg;base64,${base64Image}`
  const imageBlob = await (await fetch(imageSource)).blob()
  const formData = new FormData()

  formData.append('image', imageBlob, 'capture.jpg')
  formData.append('camera_id', 'cam_01')

  const { data } = await apiClient.post('/attendance/check-in', formData)
  return data
}

// ============= ENDPOINT ĐĂNG KÝ NHÂN VIÊN =============
export const registerEmployee = async (employeeData) => {
  const { data } = await apiClient.post('/members/register', employeeData)
  return data
}

export default apiClient
