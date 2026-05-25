<template>
  <div class="app-container">
    <AdminSidebar />

    <main class="content">
      <TopHeader title="Đăng ký đổi ca học" />

      <section class="panel-card schedule-card">
        <div class="schedule-header">
          <h2>Đăng ký Đổi ca học cho Sinh viên</h2>
        </div>

        <div class="form-section">
          <div class="input-group">
            <label>Mã Sinh Viên</label>
            <div style="display: flex; gap: 10px;">
              <input type="text" v-model="studentId" placeholder="Nhập mã sinh viên..." />
              <button class="btn-primary" @click="loadSchedule" :disabled="loading">Tải lịch</button>
            </div>
          </div>

          <div v-if="loading" class="loading">Đang tải dữ liệu...</div>
          <div v-else-if="errorMessage" class="error">{{ errorMessage }}</div>

          <div v-if="showScheduleForm" class="schedule-layout">
            <div class="left-panel">
              <h3>Đăng ký ca học mới</h3>
              <p style="font-size: 13px; color: var(--text-sub); margin-bottom: 15px;">
                Chọn ca học cho từng ngày. (Ca 1: 7h-9h40, Ca 2: 9h50-12h30, Ca 3: 13h30-16h10, Ca 4: 16h20-19h)
              </p>

              <div class="days-container">
                <div v-for="(day, index) in days" :key="index" class="day-row">
                  <div class="day-label">{{ day.name }}</div>
                  <div class="shifts">
                    <label class="shift-checkbox">
                      <input type="checkbox" v-model="schedules[index].pending_shifts" value="1" /> Ca 1
                    </label>
                    <label class="shift-checkbox">
                      <input type="checkbox" v-model="schedules[index].pending_shifts" value="2" /> Ca 2
                    </label>
                    <label class="shift-checkbox">
                      <input type="checkbox" v-model="schedules[index].pending_shifts" value="3" /> Ca 3
                    </label>
                    <label class="shift-checkbox">
                      <input type="checkbox" v-model="schedules[index].pending_shifts" value="4" /> Ca 4
                    </label>
                  </div>
                </div>
              </div>

              <div class="actions">
                <button class="btn-success" @click="saveSchedule" :disabled="saving">
                  {{ saving ? 'Đang gửi...' : 'Gửi yêu cầu đổi lịch' }}
                </button>
                <div v-if="isAdmin" style="margin-top: 20px; display: flex; gap: 10px; margin-left: auto;">
                  <button class="btn-primary" @click="approveSchedule">Duyệt lịch (Admin)</button>
                  <button class="btn-danger" @click="rejectSchedule">Không duyệt</button>
                </div>
              </div>
            </div>

            <div class="right-panel">
              <h3>Thông tin Sinh viên & Lịch học</h3>
              
              <div class="info-card" v-if="studentInfo">
                <p><strong>Mã SV:</strong> {{ studentInfo.student_id }}</p>
                <p><strong>Họ tên:</strong> {{ studentInfo.full_name }}</p>
                <p style="margin-top: 10px;">
                  <strong>Tài khoản hệ thống:</strong> 
                  <span class="badge" :class="studentInfo.is_approved ? 'approved' : 'pending'">
                    {{ studentInfo.is_approved ? '✓ Đã duyệt' : '⏳ Chờ duyệt' }}
                  </span>
                </p>
              </div>
              <div class="info-card" v-else>
                <p style="color: red; font-size: 13px;">Không tìm thấy thông tin tài khoản sinh viên này trong danh sách hệ thống.</p>
              </div>

              <h4 style="margin-top: 25px; margin-bottom: 12px; font-size: 14px;">Lịch sử đổi ca học</h4>
              <div v-if="scheduleHistory && scheduleHistory.length > 0" class="history-container">
                <div v-for="(hist, hIndex) in scheduleHistory" :key="'hist-'+hIndex" class="history-card">
                  <div class="history-header">
                    <span class="history-time">
                      <strong>Gửi lúc:</strong> {{ formatDate(hist.created_at) }}
                    </span>
                    <span class="badge" 
                          :class="hist.is_approved ? 'approved' : (hist.is_active ? 'pending' : 'rejected')">
                      {{ hist.is_approved ? 'Đã duyệt' : (hist.is_active ? 'Chờ duyệt' : 'Bị từ chối / Hủy') }}
                    </span>
                  </div>
                  <div v-if="hist.is_approved && hist.approved_at" style="font-size: 12px; color: var(--text-sub); margin-bottom: 8px;">
                    <strong>Duyệt lúc:</strong> {{ formatDate(hist.approved_at) }}
                  </div>
                  <div class="history-body">
                    <div v-for="s in hist.schedules" :key="s.day_of_week" class="history-row">
                      <span class="h-day">{{ days[s.day_of_week].name }}:</span> 
                      <span class="h-shifts">Ca {{ s.shifts }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else style="font-size: 13px; color: var(--text-sub);">
                Chưa có lịch sử thay đổi ca học nào.
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AdminSidebar from '../AdminSidebar.vue'
import TopHeader from '../TopHeader.vue'
import apiClient, { approveStudentSchedule, rejectStudentSchedule, fetchMembers, fetchScheduleHistory } from '../../shared/api'

const isAdmin = ref(!!localStorage.getItem('adminToken'))

const studentId = ref('')
const studentInfo = ref(null)
const scheduleHistory = ref([])
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const showScheduleForm = ref(false)

const days = [
  { id: 0, name: 'Thứ Hai' },
  { id: 1, name: 'Thứ Ba' },
  { id: 2, name: 'Thứ Tư' },
  { id: 3, name: 'Thứ Năm' },
  { id: 4, name: 'Thứ Sáu' },
  { id: 5, name: 'Thứ Bảy' },
]

const formatDate = (dateString) => {
  if (!dateString) return ''
  const d = new Date(dateString)
  return d.toLocaleString('vi-VN')
}

// Array to store schedule state for each day
const schedules = ref([
  { day_of_week: 0, pending_shifts: [], approved_shifts: [] },
  { day_of_week: 1, pending_shifts: [], approved_shifts: [] },
  { day_of_week: 2, pending_shifts: [], approved_shifts: [] },
  { day_of_week: 3, pending_shifts: [], approved_shifts: [] },
  { day_of_week: 4, pending_shifts: [], approved_shifts: [] },
  { day_of_week: 5, pending_shifts: [], approved_shifts: [] },
])

const loadSchedule = async () => {
  if (!studentId.value) {
    errorMessage.value = 'Vui lòng nhập mã sinh viên.'
    return
  }
  loading.value = true
  errorMessage.value = ''
  showScheduleForm.value = false
  
  // Reset schedules
  schedules.value.forEach(s => { s.pending_shifts = []; s.approved_shifts = [] })

  try {
    if (isAdmin.value) {
      const members = await fetchMembers()
      studentInfo.value = members.find(m => m.student_id === studentId.value)
    }

    const { data } = await apiClient.get(`/schedule/${studentId.value}`)
    if (data) {
      // Xác định trạng thái "bản nháp" hiện tại (ưu tiên pending, nếu không có pending thì lấy approved)
      const latestShifts = {}
      data.forEach(item => {
        // Nếu là pending, ghi đè. Nếu là approved mà chưa có gì thì lấy.
        if (!latestShifts[item.day_of_week] || item.is_approved === false) {
          latestShifts[item.day_of_week] = item.shifts.split(',').map(s => s.trim())
        }
      })
      
      Object.keys(latestShifts).forEach(day => {
        const dayItem = schedules.value.find(s => s.day_of_week === parseInt(day))
        if (dayItem) {
          dayItem.pending_shifts = latestShifts[day]
        }
      })
    }
    
    // Fetch history
    try {
      scheduleHistory.value = await fetchScheduleHistory(studentId.value)
    } catch (e) {
      console.error("Lỗi khi tải lịch sử:", e)
    }

    showScheduleForm.value = true
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải lịch học (kiểm tra lại mã SV).'
  } finally {
    loading.value = false
  }
}

const saveSchedule = async () => {
  saving.value = true
  
  const payloadSchedules = schedules.value
    .filter(s => s.pending_shifts.length > 0)
    .map(s => ({
      day_of_week: s.day_of_week,
      shifts: s.pending_shifts.join(',')
    }))

  if (payloadSchedules.length === 0) {
    alert('Vui lòng chọn ít nhất 1 ca học trước khi gửi yêu cầu.')
    saving.value = false
    return
  }

  try {
    await apiClient.post(`/schedule/${studentId.value}`, { schedules: payloadSchedules })
    alert('Gửi yêu cầu đổi lịch học thành công! Vui lòng chờ Giảng viên duyệt.')
  } catch (error) {
    alert(error.response?.data?.detail || 'Lỗi khi lưu lịch học.')
  } finally {
    saving.value = false
  }
}

const approveSchedule = async () => {
  try {
    await approveStudentSchedule(studentId.value)
    alert('Duyệt lịch học thành công!')
    await loadSchedule() // reload lại để cập nhật trạng thái
  } catch (error) {
    alert(error.response?.data?.detail || 'Lỗi khi duyệt lịch.')
  }
}

const rejectSchedule = async () => {
  if (!confirm('Bạn có chắc chắn muốn từ chối yêu cầu đổi lịch này?')) return
  try {
    await rejectStudentSchedule(studentId.value)
    alert('Đã từ chối lịch học!')
    await loadSchedule()
  } catch (error) {
    alert(error.response?.data?.detail || 'Lỗi khi từ chối lịch.')
  }
}
</script>

<style scoped>
.app-container {
  display: flex;
  width: 100%;
  min-height: 100vh;
  overflow: hidden;
}

main.content {
  flex-grow: 1;
  padding: 25px 30px;
  overflow-y: auto;
}

.schedule-card {
  margin-top: 10px;
  padding: 20px;
}

.schedule-header h2 {
  font-size: 16px;
  margin-top: 0;
  margin-bottom: 20px;
}

.input-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
}

.input-group input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  width: 250px;
}

.btn-primary {
  background-color: var(--primary-color);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
}

.btn-success {
  background-color: var(--success-color);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 20px;
}

.loading {
  margin-top: 15px;
  color: var(--text-sub);
  font-size: 13px;
}

.error {
  margin-top: 15px;
  color: var(--danger-color);
  font-size: 13px;
}

.schedule-layout {
  display: flex;
  gap: 30px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
  align-items: flex-start;
}

.left-panel {
  flex: 1;
  max-width: 550px;
}

.right-panel {
  flex: 1;
  background-color: #f8fafc;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  min-width: 300px;
}

.info-card {
  background: white;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.info-card p {
  margin: 8px 0;
  font-size: 14px;
}

.schedule-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-row {
  display: flex;
  flex-direction: column;
  background: white;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.summary-row .day-label {
  font-weight: 600;
  margin-bottom: 8px;
  color: #334155;
  font-size: 13px;
}

.history-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 5px;
}

.history-card {
  background: white;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.history-body {
  border-top: 1px dashed #e2e8f0;
  padding-top: 8px;
}

.history-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 4px;
}

.h-day {
  font-weight: 500;
  color: #475569;
}

.days-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 600px;
}

.day-row {
  display: flex;
  align-items: center;
  background-color: #f8fafc;
  padding: 12px 15px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  gap: 10px;
}

.status-badge {
  margin-left: auto;
}

.badge {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  white-space: nowrap;
}

.badge.approved {
  background-color: #dcfce7;
  color: #16a34a;
  border: 1px solid #86efac;
}

.badge.pending {
  background-color: #fef9c3;
  color: #92400e;
  border: 1px solid #fde68a;
}

.badge.rejected {
  background-color: #f3f4f6;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.btn-danger {
  background-color: #ef4444;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
}

.btn-danger:hover {
  background-color: #dc2626;
}

.day-label {
  width: 100px;
  font-weight: 500;
  font-size: 14px;
}

.shifts {
  display: flex;
  gap: 15px;
}

.shift-checkbox {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  cursor: pointer;
}

.actions {
  display: flex;
  justify-content: flex-start;
}
</style>
