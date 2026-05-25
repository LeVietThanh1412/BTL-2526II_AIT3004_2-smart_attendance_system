<template>
  <div class="app-container">
    <AdminSidebar />

    <main class="content">
      <TopHeader title="Quản lý Sinh viên" />

      <div class="members-container">
        <div class="header-actions">
          <h2>Quản lý Sinh viên</h2>
          <button @click="loadMembers" class="btn-refresh">Làm mới</button>
        </div>

    <div v-if="loading" class="loading">Đang tải dữ liệu...</div>
    
    <div v-else class="table-wrapper">
      <table class="members-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Mã SV</th>
            <th>Họ Tên</th>
            <th>Trạng Thái</th>
            <th>Thao Tác</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="member in members" :key="member.id">
            <td>{{ member.id }}</td>
            <td>{{ member.student_id }}</td>
            <td>{{ member.full_name }}</td>
            <td>
              <span :class="['badge', member.is_approved ? 'badge-success' : 'badge-warning']">
                {{ member.is_approved ? 'Đã duyệt' : 'Chưa duyệt' }}
              </span>
            </td>
            <td class="actions">
              <button 
                v-if="!member.is_approved" 
                @click="handleApprove(member.student_id)" 
                class="btn btn-approve">
                Duyệt
              </button>
              <button 
                @click="handleDelete(member.student_id, member.full_name)" 
                class="btn btn-delete">
                Xóa
              </button>
            </td>
          </tr>
          <tr v-if="members.length === 0">
            <td colspan="5" class="empty-state">Không có sinh viên nào.</td>
          </tr>
        </tbody>
      </table>
    </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AdminSidebar from '../AdminSidebar.vue'
import TopHeader from '../TopHeader.vue'
import { fetchMembers, approveMember, deleteMember } from '../../shared/api'

const members = ref([])
const loading = ref(false)

const loadMembers = async () => {
  loading.value = true
  try {
    members.value = await fetchMembers()
  } catch (err) {
    alert('Lỗi tải danh sách sinh viên')
  } finally {
    loading.value = false
  }
}

const handleApprove = async (studentId) => {
  if (!confirm(`Xác nhận duyệt sinh viên ${studentId}?`)) return
  try {
    await approveMember(studentId)
    alert('Duyệt thành công!')
    await loadMembers()
  } catch (err) {
    alert('Lỗi khi duyệt sinh viên')
  }
}

const handleDelete = async (studentId, name) => {
  if (!confirm(`Bạn có chắc chắn muốn xóa TOÀN BỘ dữ liệu của sinh viên ${name} (${studentId}) không?\nHành động này không thể hoàn tác!`)) return
  try {
    await deleteMember(studentId)
    alert('Đã xóa sinh viên và dữ liệu nhận diện.')
    await loadMembers()
  } catch (err) {
    alert('Lỗi khi xóa sinh viên')
  }
}

onMounted(() => {
  loadMembers()
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

.members-container {
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  margin-top: 10px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.header-actions h2 {
  margin: 0;
  color: #1e293b;
}

.btn-refresh {
  padding: 0.5rem 1rem;
  background-color: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  color: #334155;
}

.btn-refresh:hover {
  background-color: #e2e8f0;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #64748b;
}

.table-wrapper {
  overflow-x: auto;
}

.members-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.members-table th, .members-table td {
  padding: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.members-table th {
  background-color: #f8fafc;
  color: #475569;
  font-weight: 600;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.badge-success {
  background-color: #dcfce7;
  color: #166534;
}

.badge-warning {
  background-color: #fef9c3;
  color: #854d0e;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.375rem 0.75rem;
  border-radius: 4px;
  border: none;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-approve {
  background-color: #3b82f6;
  color: white;
}

.btn-approve:hover {
  background-color: #2563eb;
}

.btn-delete {
  background-color: #ef4444;
  color: white;
}

.btn-delete:hover {
  background-color: #dc2626;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #94a3b8;
}
</style>
