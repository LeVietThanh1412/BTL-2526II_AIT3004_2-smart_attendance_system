<template>
  <div class="app-container">
    <AdminSidebar />

    <main class="content">
      <TopHeader title="Đăng ký điểm danh" />

      <section class="register-layout">
        <div class="panel-card form-card">
          <div class="section-heading">
            <h2>Hồ sơ nhân sự</h2>
            <p>Nhập thông tin và tải lên ít nhất 3 ảnh khuôn mặt rõ nét.</p>
          </div>

          <form class="register-form" @submit.prevent="handleSubmit">
            <label>
              <span>Mã nhân viên / sinh viên</span>
              <input v-model.trim="studentId" type="text" placeholder="VD: SV2401" />
            </label>

            <label>
              <span>Họ và tên</span>
              <input v-model.trim="fullName" type="text" placeholder="VD: Nguyễn Văn A" />
            </label>

            <label>
              <span>Ảnh khuôn mặt</span>
              <input type="file" accept="image/*" multiple @change="handleImageSelection" />
            </label>

            <p class="helper-text">Đã chọn {{ selectedImageCount }} ảnh. Hệ thống cần tối thiểu {{ minimumImages }} ảnh để đăng ký.</p>

            <button class="submit-btn" type="submit" :disabled="isSubmitting">
              {{ isSubmitting ? 'Đang đăng ký...' : 'Gửi đăng ký' }}
            </button>

            <p v-if="statusMessage" class="status-message" :class="statusTone">{{ statusMessage }}</p>
          </form>
        </div>

        <div class="panel-card preview-card">
          <div class="section-heading">
            <h2>Xem trước ảnh</h2>
            <p>Các ảnh đã chọn sẽ được chuyển sang base64 trước khi gửi backend.</p>
          </div>

          <div v-if="previewItems.length" class="preview-grid">
            <figure v-for="item in previewItems" :key="item.name" class="preview-item">
              <img :src="item.url" :alt="item.name" />
              <figcaption>{{ item.name }}</figcaption>
            </figure>
          </div>

          <div v-else class="empty-state">
            Chưa có ảnh nào được chọn.
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

import AdminSidebar from '../AdminSidebar.vue'
import TopHeader from '../TopHeader.vue'
import { registerEmployee } from '../../shared/api'

const studentId = ref('')
const fullName = ref('')
const selectedImages = ref([])
const previewItems = ref([])
const isSubmitting = ref(false)
const statusMessage = ref('')
const statusTone = ref('neutral')

const minimumImages = 3
const selectedImageCount = computed(() => selectedImages.value.length)

const clearPreviewItems = () => {
  previewItems.value.forEach((item) => URL.revokeObjectURL(item.url))
  previewItems.value = []
}

const fileToBase64 = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = () => {
      const result = String(reader.result || '')
      resolve(result)
    }

    reader.onerror = () => reject(new Error(`Không thể đọc file ${file.name}`))
    reader.readAsDataURL(file)
  })

const handleImageSelection = (event) => {
  clearPreviewItems()

  const files = Array.from(event.target.files || []).filter((file) => file.type.startsWith('image/'))
  selectedImages.value = files
  previewItems.value = files.map((file) => ({
    name: file.name,
    url: URL.createObjectURL(file),
  }))

  statusMessage.value = ''
  statusTone.value = 'neutral'
}

const handleSubmit = async () => {
  if (!studentId.value || !fullName.value) {
    statusMessage.value = 'Vui lòng nhập đủ mã và họ tên.'
    statusTone.value = 'error'
    return
  }

  if (selectedImageCount.value < minimumImages) {
    statusMessage.value = `Cần ít nhất ${minimumImages} ảnh để đăng ký.`
    statusTone.value = 'error'
    return
  }

  isSubmitting.value = true
  statusMessage.value = ''

  try {
    const imagesBase64 = await Promise.all(selectedImages.value.map((file) => fileToBase64(file)))

    const response = await registerEmployee({
      student_id: studentId.value,
      name: fullName.value,
      images_base64: imagesBase64,
    })

    statusMessage.value = `Đăng ký thành công: ${response.name} (${response.accepted_images} ảnh hợp lệ).`
    statusTone.value = 'success'
  } catch (error) {
    console.error('[v0] Lỗi đăng ký nhân sự:', error.message)
    statusMessage.value = 'Không thể kết nối backend, nhưng form đã hợp lệ và sẵn sàng gửi.'
    statusTone.value = 'warning'
  } finally {
    isSubmitting.value = false
  }
}

onBeforeUnmount(() => {
  clearPreviewItems()
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

.register-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 20px;
  align-items: start;
}

.section-heading h2 {
  margin: 0 0 6px;
  font-size: 18px;
}

.section-heading p {
  margin: 0;
  color: var(--text-sub);
  font-size: 13px;
}

.register-form {
  display: grid;
  gap: 16px;
  margin-top: 20px;
}

.register-form label {
  display: grid;
  gap: 8px;
}

.register-form span {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.register-form input[type='text'],
.register-form input[type='file'] {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 14px;
  font: inherit;
  background: #fff;
}

.register-form input[type='file'] {
  padding: 10px 14px;
}

.helper-text {
  margin: 0;
  color: var(--text-sub);
  font-size: 12px;
}

.submit-btn {
  border: 0;
  border-radius: 12px;
  background: var(--primary-color);
  color: #fff;
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.status-message {
  margin: 0;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 13px;
}

.status-message.success {
  background: #ecfdf5;
  color: var(--success-color);
}

.status-message.warning {
  background: #fffbeb;
  color: var(--warning-color);
}

.status-message.error {
  background: #fef2f2;
  color: var(--danger-color);
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 14px;
  margin-top: 20px;
}

.preview-item {
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: #fff;
}

.preview-item img {
  display: block;
  width: 100%;
  height: 140px;
  object-fit: cover;
}

.preview-item figcaption {
  padding: 10px 12px;
  font-size: 12px;
  color: var(--text-sub);
  word-break: break-word;
}

.empty-state {
  margin-top: 20px;
  border: 1px dashed var(--border-color);
  border-radius: 14px;
  padding: 24px;
  text-align: center;
  color: var(--text-sub);
}

@media (max-width: 1100px) {
  .register-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .app-container {
    flex-direction: column;
  }

  main.content {
    padding: 18px;
  }
}
</style>