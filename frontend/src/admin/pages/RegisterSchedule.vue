<template>
  <div class="app-container">
    <AdminSidebar />

    <main class="content">
      <TopHeader title="Đăng ký lịch học" />

      <section class="panel-card schedule-card">
        <div class="schedule-header">
          <h2>Đăng ký Lịch học cho Sinh viên</h2>
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

          <div v-if="showScheduleForm" class="schedule-form">
            <h3>Lịch học của {{ studentId }}</h3>
            <p style="font-size: 13px; color: var(--text-sub); margin-bottom: 15px;">
              Chọn ca học cho từng ngày. (Ca 1: 7h-9h40, Ca 2: 9h50-12h30, Ca 3: 13h30-16h10, Ca 4: 16h20-19h)
            </p>

            <div class="days-container">
              <div v-for="(day, index) in days" :key="index" class="day-row">
                <div class="day-label">{{ day.name }}</div>
                <div class="shifts">
                  <label class="shift-checkbox">
                    <input type="checkbox" v-model="schedules[index].shifts" value="1" /> Ca 1
                  </label>
                  <label class="shift-checkbox">
                    <input type="checkbox" v-model="schedules[index].shifts" value="2" /> Ca 2
                  </label>
                  <label class="shift-checkbox">
                    <input type="checkbox" v-model="schedules[index].shifts" value="3" /> Ca 3
                  </label>
                  <label class="shift-checkbox">
                    <input type="checkbox" v-model="schedules[index].shifts" value="4" /> Ca 4
                  </label>
                </div>
              </div>
            </div>

            <div class="actions">
              <button class="btn-success" @click="saveSchedule" :disabled="saving">
                {{ saving ? 'Đang lưu...' : 'Lưu lịch học' }}
              </button>
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
import apiClient from '../../shared/api'

const studentId = ref('')
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

// Array to store schedule state for each day
const schedules = ref([
  { day_of_week: 0, shifts: [] },
  { day_of_week: 1, shifts: [] },
  { day_of_week: 2, shifts: [] },
  { day_of_week: 3, shifts: [] },
  { day_of_week: 4, shifts: [] },
  { day_of_week: 5, shifts: [] },
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
  schedules.value.forEach(s => s.shifts = [])

  try {
    const { data } = await apiClient.get(`/schedule/${studentId.value}`)
    if (data) {
      data.forEach(item => {
        const dayItem = schedules.value.find(s => s.day_of_week === item.day_of_week)
        if (dayItem) {
          dayItem.shifts = item.shifts.split(',').map(s => s.trim())
        }
      })
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
    .filter(s => s.shifts.length > 0)
    .map(s => ({
      day_of_week: s.day_of_week,
      shifts: s.shifts.join(',')
    }))

  try {
    await apiClient.post(`/schedule/${studentId.value}`, { schedules: payloadSchedules })
    alert('Lưu lịch học thành công!')
  } catch (error) {
    alert(error.response?.data?.detail || 'Lỗi khi lưu lịch học.')
  } finally {
    saving.value = false
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

.schedule-form {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.days-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 500px;
}

.day-row {
  display: flex;
  align-items: center;
  background-color: #f8fafc;
  padding: 12px 15px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
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
