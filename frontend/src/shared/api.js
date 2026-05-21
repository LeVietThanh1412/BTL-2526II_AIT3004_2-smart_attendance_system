// =====================================================================
// shared/api.js - Lớp gọi API dùng chung cho toàn dự án
// Tất cả request đều đi qua Nginx Gateway (/api/*)
// =====================================================================

import axios from 'axios'

// Tạo instance axios riêng để cấu hình baseURL & interceptors tập trung
const apiClient = axios.create({
  baseURL: '/api/v1',

  timeout: 120000,

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
  const { data } = await apiClient.get('/dashboard/statistics')
  return data
}

// ============= ENDPOINTS HOẠT ĐỘNG =============
export const fetchRecentActivities = async (limit = 10) => {
  const { data } = await apiClient.get('/dashboard/recent-activities', {
    params: { limit },
  })
  return data?.activities ?? []
}

// ============= ENDPOINTS THÔNG BÁO =============
export const fetchNotificationCount = async () => {
  const { data } = await apiClient.get('/dashboard/notifications')
  return data
}

// ============= ENDPOINTS LOG ĐIỂM DANH =============
export const fetchAttendanceLogs = async (page = 1, pageSize = 20) => {
  const { data } = await apiClient.get('/dashboard/attendance-logs', {
    params: { page, page_size: pageSize },
  })
  return data
}

// ============= ENDPOINT ĐIỂM DANH (gửi ảnh base64 lên AI) =============
export const submitCheckIn = async (base64Image, studentId) => {
  const imageSource = base64Image.startsWith('data:')
    ? base64Image
    : `data:image/jpeg;base64,${base64Image}`
  const imageBlob = await (await fetch(imageSource)).blob()
  const formData = new FormData()

  formData.append('image', imageBlob, 'capture.jpg')
  formData.append('student_id', studentId)
  formData.append('camera_id', 'cam_01')

  const { data } = await apiClient.post('/attendance/check-in', formData)
  return data
}

// ============= ENDPOINT ĐĂNG KÝ NHÂN VIÊN =============
export const registerEmployee = async (employeeData) => {
  const { data } = await apiClient.post('/members/register', employeeData)
  return data
}

export const registerEmployeeVideo = async ({ student_id, name, videoFile }) => {
  if (!videoFile) {
    throw new Error('Thiếu file video để đăng ký.')
  }

  const formData = new FormData()
  formData.append('student_id', student_id)
  formData.append('name', name)
  formData.append('video', videoFile, videoFile.name || 'register.webm')

  const { data } = await apiClient.post('/members/register-video', formData, {
    timeout: 180000,
  })
  return data
}

export default apiClient
