<template>
  <div class="app-container">
    <AdminSidebar />

    <main class="content">
      <TopHeader title="Lịch sử điểm danh" />

      <section class="panel-card logs-card">
        <div class="logs-header">
          <h2>Nhật ký điểm danh</h2>
          <span class="total-count">Tổng: {{ totalItems }}</span>
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
                  <td>{{ item.time }} - {{ item.date }}</td>
                  <td>
                    <span class="status-pill" :class="item.statusColor">{{ item.status }}</span>
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
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import AdminSidebar from '../AdminSidebar.vue'
import TopHeader from '../TopHeader.vue'
import { fetchAttendanceLogs } from '../../shared/api'

const logs = ref([])
const loading = ref(true)
const errorMessage = ref('')
const page = ref(1)
const pageSize = ref(10)
const totalPages = ref(1)
const totalItems = ref(0)

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

onMounted(loadLogs)
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

.total-count {
  font-size: 12px;
  color: var(--text-sub);
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
</style>
