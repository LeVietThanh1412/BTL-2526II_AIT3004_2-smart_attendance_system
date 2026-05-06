// =====================================================================
// shared/dateUtils.js - Các hàm format ngày tháng dùng chung
// =====================================================================

const DAYS_VI = ['Chủ nhật', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7']

// Đệm số 0 ở đầu (ví dụ: 7 -> 07)
const pad = (n) => String(n).padStart(2, '0')

// Trả về chuỗi giờ "HH:MM:SS"
export function formatTime(date = new Date()) {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

// Trả về chuỗi ngày "Thứ X, dd/mm/yyyy"
export function formatDate(date = new Date()) {
  const dayOfWeek = DAYS_VI[date.getDay()]
  return `${dayOfWeek}, ${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`
}

// Trả về "dd/mm/yyyy"
export function formatShortDate(date = new Date()) {
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`
}
