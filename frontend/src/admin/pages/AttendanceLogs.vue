<template>
  <div class="app-container">
    <AdminSidebar />

    <main class="content">
      <TopHeader title="Lịch sử điểm danh" />

      <section class="panel-card logs-card">
        <div class="logs-header">
          <h2>Nhật ký điểm danh</h2>
          <div class="header-actions">
            <span class="total-count">Tổng: {{ totalItems }}</span>
            <button class="export-btn" @click="exportCSV">Xuất Excel</button>
          </div>
        </div>

        <div v-if="loading" class="loading">Đang tải dữ liệu...</div>
        <div v-else-if="errorMessage" class="loading error">{{ errorMessage }}</div>

        <div v-else>
          <div class="table-wrap">
            <table class="logs-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Mã SV</th>
                  <th>Họ tên</th>
                  <th>Thời gian</th>
                  <th>Trạng thái</th>
                  <th>Camera</th>
                  <th>Độ tin cậy</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in logs" :key="item.id">
                  <td>{{ rowIndex(idx) }}</td>
                  <td>{{ item.student_id || 'Không rõ' }}</td>
                  <td>{{ item.name }}</td>
                  <td>
                    <div style="font-weight: 500; color: #334155;">In: {{ item.time }}</div>
                    <div style="color: #64748b; margin-top: 2px;">Out: {{ item.check_out_time || '--:--' }}</div>
                    <div style="font-size: 11px; margin-top: 4px; color: #94a3b8;">{{ item.date }}</div>
                  </td>
                  <td>
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                      <div style="display: flex; align-items: center; gap: 6px;">
                        <span class="status-pill" :class="item.statusColor">{{ item.status }}</span>
                        <button class="btn-edit" @click="openOverrideModal(item)" title="Sửa trạng thái">✏️</button>
                      </div>
                      <small v-if="item.override_reason" class="override-reason">Lý do: {{ item.override_reason }}</small>
                    </div>
                  </td>
                  <td>{{ item.camera_id }}</td>
                  <td>{{ formatScore(item.confidence_score) }}</td>
                </tr>
              </tbody>
            </table>

            <div v-if="!logs.length" class="empty-state">Chưa có log điểm danh.</div>
          </div>

          <div class="pagination">
            <button class="page-btn" :disabled="page <= 1" @click="goPrev">Trước</button>
            <span>Trang {{ page }} / {{ totalPages }}</span>
            <button class="page-btn" :disabled="page >= totalPages" @click="goNext">Sau</button>
          </div>
        </div>
      </section>

      <!-- Override Modal -->
      <div v-if="showOverrideModal" class="modal-overlay">
        <div class="modal-content">
          <h3>Sửa trạng thái điểm danh</h3>
          <p>Sinh viên: <strong>{{ currentEditLog?.name }}</strong></p>
          
          <div class="form-group">
            <label>Trạng thái</label>
            <select v-model="editData.status">
              <option value="success">Thành công (Đúng/Muộn theo hệ thống)</option>
              <option value="failed">Nhận diện lỗi / Thất bại</option>
              <option value="absent_unexcused">Vắng không phép</option>
              <option value="absent_excused">Vắng có phép</option>
              <option value="present_incomplete">Quên check-out</option>
            </select>
          </div>
          
          <div class="form-group" v-if="editData.status === 'success'">
            <label>Sửa Đi đúng giờ / Vào muộn</label>
            <div style="display: flex; gap: 15px; margin-top: 5px;">
              <label style="display: flex; align-items: center; gap: 5px; font-weight: normal;">
                <input type="radio" :value="false" v-model="editData.is_late" />
                Vào đúng giờ
              </label>
              <label style="display: flex; align-items: center; gap: 5px; font-weight: normal;">
                <input type="radio" :value="true" v-model="editData.is_late" />
                Vào muộn
              </label>
            </div>
          </div>
          
          <div class="form-group">
            <label>Lý do thay đổi</label>
            <input type="text" v-model="editData.reason" placeholder="Ví dụ: Giảng viên cho phép..." required />
          </div>
          
          <div class="modal-actions">
            <button class="btn-cancel" @click="showOverrideModal = false">Hủy</button>
            <button class="btn-save" @click="saveOverride">Lưu</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

import AdminSidebar from '../AdminSidebar.vue'
import TopHeader from '../TopHeader.vue'
import { fetchAttendanceLogs, overrideLateStatus } from '../../shared/api'

const logs = ref([])
const loading = ref(true)
const errorMessage = ref('')
const page = ref(1)
const pageSize = ref(10)
const totalPages = ref(1)
const totalItems = ref(0)

const showOverrideModal = ref(false)
const currentEditLog = ref(null)
const editData = ref({
  status: 'success',
  is_late: false,
  reason: ''
})

const openOverrideModal = (log) => {
  currentEditLog.value = log
  editData.value.status = log.raw_status || 'success'
  editData.value.is_late = log.is_late_override ?? false
  editData.value.reason = log.override_reason || ''
  showOverrideModal.value = true
}

const saveOverride = async () => {
  if (!editData.value.reason) {
    alert('Vui lòng nhập lý do.')
    return
  }
  try {
    await overrideLateStatus(currentEditLog.value.id, editData.value.status, editData.value.is_late, editData.value.reason)
    showOverrideModal.value = false
    await loadLogs()
  } catch (err) {
    alert('Lỗi khi lưu trạng thái')
  }
}

const loadLogs = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const data = await fetchAttendanceLogs(page.value, pageSize.value)
    logs.value = data?.items ?? []
    totalPages.value = data?.total_pages ?? 1
    totalItems.value = data?.total ?? 0
  } catch (error) {
    console.error('[v0] Lỗi tải nhật ký điểm danh:', error.message)
    logs.value = []
    totalPages.value = 1
    totalItems.value = 0
    errorMessage.value = 'Không thể tải nhật ký điểm danh. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}

const rowIndex = (index) => (page.value - 1) * pageSize.value + index + 1

const formatScore = (score) => {
  const numeric = Number(score)
  return Number.isFinite(numeric) ? numeric.toFixed(4) : '--'
}

const goPrev = async () => {
  if (page.value <= 1) return
  page.value -= 1
  await loadLogs()
}

const goNext = async () => {
  if (page.value >= totalPages.value) return
  page.value += 1
  await loadLogs()
}

const exportCSV = () => {
  window.open('/api/v1/dashboard/export-attendance', '_blank')
}

let pollingInterval = null

onMounted(() => {
  loadLogs()
  pollingInterval = setInterval(loadLogs, 5000)
})

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
})
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

.logs-card {
  margin-top: 10px;
}

.logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.logs-header h2 {
  margin: 0;
  font-size: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.total-count {
  font-size: 12px;
  color: var(--text-sub);
}

.export-btn {
  background-color: var(--success-color);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.export-btn:hover {
  opacity: 0.9;
}

.table-wrap {
  margin-top: 16px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  overflow: hidden;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.logs-table thead {
  background: #f8fafc;
}

.logs-table th,
.logs-table td {
  padding: 12px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.logs-table tbody tr:hover {
  background: #f9fafb;
}

.status-pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.status-pill.green {
  background-color: #ecfdf5;
  color: var(--success-color);
}

.status-pill.red {
  background-color: #fef2f2;
  color: var(--danger-color);
}

.status-pill.yellow {
  background-color: #fffbeb;
  color: var(--warning-color);
}

.loading {
  padding: 20px;
  text-align: center;
  color: var(--text-sub);
  font-size: 13px;
}

.loading.error {
  color: var(--danger-color);
}

.empty-state {
  padding: 20px;
  text-align: center;
  color: var(--text-sub);
  font-size: 13px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-sub);
}

.page-btn {
  border: 1px solid var(--border-color);
  background: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
}

.page-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .app-container {
    flex-direction: column;
  }

  main.content {
    padding: 18px;
  }

  .logs-table th,
  .logs-table td {
    padding: 10px 12px;
  }
}

.btn-edit {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 0.6;
}

.btn-edit:hover {
  background: #f1f5f9;
  opacity: 1;
}

.override-reason {
  color: #64748b;
  font-size: 11px;
}

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 20px 25px;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 10px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 5px;
}

.form-group select,
.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.btn-cancel {
  padding: 8px 16px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  cursor: pointer;
}

.btn-save {
  padding: 8px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
</style>
