// =====================================================================
// shared/api.js - Lớp gọi API dùng chung cho toàn dự án
// Tất cả request đều đi qua Nginx Gateway (/api/*)
// =====================================================================

import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

// Tự động gắn Token vào tất cả request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('adminToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => Promise.reject(error))


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

// ============= ENDPOINTS ADMIN & AUTH =============
export const loginAdmin = async (username, password) => {
  const { data } = await apiClient.post('/auth/login', { username, password })
  return data
}

export const fetchMembers = async () => {
  const { data } = await apiClient.get('/members')
  return data?.items ?? []
}

export const approveMember = async (studentId) => {
  const { data } = await apiClient.post(`/members/${studentId}/approve`)
  return data
}

export const approveStudentSchedule = async (studentId) => {
  const { data } = await apiClient.post(`/schedule/${studentId}/approve`)
  return data
}

export const fetchScheduleHistory = async (studentId) => {
  const { data } = await apiClient.get(`/schedule/${studentId}/history`)
  return data
}

export const deleteMember = async (studentId) => {
  const { data } = await apiClient.delete(`/members/${studentId}`)
  return data
}

export const overrideLateStatus = async (attendanceId, status, is_late_override, override_reason) => {
  const { data } = await apiClient.put(`/attendance/${attendanceId}/override`, {
    status,
    is_late_override,
    override_reason
  })
  return data
}

export default apiClient
