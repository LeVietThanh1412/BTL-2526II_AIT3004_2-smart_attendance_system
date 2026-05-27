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

            <div class="mode-toggle">
              <label :class="{ active: registrationMode === 'images' }">
                <input v-model="registrationMode" type="radio" value="images" :disabled="isRecording" />
                Đăng ký bằng ảnh
              </label>
              <label :class="{ active: registrationMode === 'video' }">
                <input v-model="registrationMode" type="radio" value="video" :disabled="isRecording" />
                Đăng ký bằng video
              </label>
            </div>

            <label v-if="registrationMode === 'images'">
              <span>Ảnh khuôn mặt</span>
              <input type="file" accept="image/*" multiple @change="handleImageSelection" />
            </label>

            <div v-else class="video-panel">
              <span class="field-label">Video khuôn mặt</span>
              <div class="video-actions">
                <button type="button" class="secondary-btn" @click="startVideoPreview" :disabled="isRecording">
                  Bật camera
                </button>
                <button type="button" class="secondary-btn" @click="startRecording" :disabled="isRecording">
                  Bắt đầu quay
                </button>
                <button type="button" class="secondary-btn" @click="stopRecording" :disabled="!isRecording">
                  Dừng quay
                </button>
                <label class="file-btn" :class="{ disabled: isRecording }">
                  <input type="file" accept="video/*" :disabled="isRecording" @change="handleVideoSelection" />
                  Chọn video
                </label>
                <button
                  type="button"
                  class="ghost-btn"
                  @click="clearVideoSelection"
                  :disabled="isRecording || (!videoFile && !videoPreviewUrl && !isVideoPreviewOn)"
                >
                  Xóa video
                </button>
              </div>
              <p class="helper-text">Quay 10-20 giây, khuôn mặt rõ nét và đủ ánh sáng.</p>
            </div>

            <p v-if="registrationMode === 'images'" class="helper-text">
              Đã chọn {{ selectedImageCount }} ảnh. Hệ thống cần tối thiểu {{ minimumImages }} ảnh để đăng ký.
            </p>

            <div class="schedule-form" style="margin-top: 15px; border-top: 1px solid var(--border-color); padding-top: 15px;">
              <span class="field-label" style="display: block; margin-bottom: 10px;">Đăng ký ca học (Chọn ít nhất 1 ca)</span>
              <div class="days-container">
                <div v-for="(day, index) in days" :key="index" class="day-row">
                  <div class="day-label">{{ day.name }}</div>
                  <div class="shifts">
                    <label class="shift-checkbox"><input type="checkbox" v-model="schedules[index].shifts" value="1" /> Ca 1</label>
                    <label class="shift-checkbox"><input type="checkbox" v-model="schedules[index].shifts" value="2" /> Ca 2</label>
                    <label class="shift-checkbox"><input type="checkbox" v-model="schedules[index].shifts" value="3" /> Ca 3</label>
                    <label class="shift-checkbox"><input type="checkbox" v-model="schedules[index].shifts" value="4" /> Ca 4</label>
                  </div>
                </div>
              </div>
            </div>

            <button class="submit-btn" type="submit" :disabled="isSubmitting">
              {{ isSubmitting ? 'Đang đăng ký...' : 'Gửi đăng ký' }}
            </button>

            <p v-if="statusMessage" class="status-message" :class="statusTone">{{ statusMessage }}</p>
          </form>
        </div>

        <div class="panel-card preview-card">
          <div class="section-heading">
            <h2>{{ registrationMode === 'images' ? 'Xem trước ảnh' : 'Xem trước video' }}</h2>
            <p v-if="registrationMode === 'images'">Các ảnh đã chọn sẽ được chuyển sang dạng base64 trước khi gửi lên máy chủ.</p>
            <p v-else>Video sẽ được gửi lên hệ thống để trích xuất khung hình khuôn mặt.</p>
          </div>

          <div v-if="registrationMode === 'images'">
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

          <div v-else class="video-preview">
            <video
              ref="videoPreviewEl"
              class="video-preview-el"
              :controls="Boolean(videoPreviewUrl)"
              :muted="!videoPreviewUrl"
              autoplay
              playsinline
              v-show="isRecording || videoPreviewUrl || isVideoPreviewOn"
            ></video>
            <div v-if="!isRecording && !videoPreviewUrl && !isVideoPreviewOn" class="empty-state">
              Chưa có video nào được chọn.
            </div>
            <p v-if="videoFile" class="video-meta">Tệp: {{ videoFile.name }}</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import AdminSidebar from '../AdminSidebar.vue'
import TopHeader from '../TopHeader.vue'
import apiClient, { registerEmployee, registerEmployeeVideo } from '../../shared/api'

const studentId = ref('')
const fullName = ref('')
const selectedImages = ref([])
const previewItems = ref([])
const registrationMode = ref('images')
const videoPreviewEl = ref(null)
const videoPreviewUrl = ref('')
const videoFile = ref(null)
const isRecording = ref(false)
const isVideoPreviewOn = ref(false)
const isSubmitting = ref(false)
const statusMessage = ref('')
const statusTone = ref('neutral')

const minimumImages = 3
const selectedImageCount = computed(() => selectedImages.value.length)

const days = [
  { id: 0, name: 'Thứ Hai' }, { id: 1, name: 'Thứ Ba' }, { id: 2, name: 'Thứ Tư' },
  { id: 3, name: 'Thứ Năm' }, { id: 4, name: 'Thứ Sáu' }, { id: 5, name: 'Thứ Bảy' },
]

const schedules = ref([
  { day_of_week: 0, shifts: [] }, { day_of_week: 1, shifts: [] }, { day_of_week: 2, shifts: [] },
  { day_of_week: 3, shifts: [] }, { day_of_week: 4, shifts: [] }, { day_of_week: 5, shifts: [] },
])

let videoStream = null
let mediaRecorder = null
let recordedChunks = []

const clearPreviewItems = () => {
  previewItems.value.forEach((item) => URL.revokeObjectURL(item.url))
  previewItems.value = []
}

const resetVideoSelection = () => {
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value)
  }
  videoPreviewUrl.value = ''
  videoFile.value = null

  if (videoPreviewEl.value) {
    videoPreviewEl.value.pause?.()
    videoPreviewEl.value.removeAttribute('src')
    videoPreviewEl.value.load?.()
    videoPreviewEl.value.controls = false
    videoPreviewEl.value.muted = true
  }
}

const stopVideoStream = () => {
  if (videoStream) {
    videoStream.getTracks().forEach((track) => track.stop())
    videoStream = null
  }
  if (videoPreviewEl.value) {
    videoPreviewEl.value.srcObject = null
  }
  isVideoPreviewOn.value = false
}

const setVideoSelection = (file) => {
  resetVideoSelection()
  videoFile.value = file
  videoPreviewUrl.value = URL.createObjectURL(file)

  if (videoPreviewEl.value) {
    videoPreviewEl.value.srcObject = null
    videoPreviewEl.value.src = videoPreviewUrl.value
    videoPreviewEl.value.muted = false
    videoPreviewEl.value.controls = true
  }
}

const getSupportedMimeType = () => {
  if (!window.MediaRecorder?.isTypeSupported) return ''
  const candidates = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm', 'video/mp4']
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || ''
}

const startVideoPreview = async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    statusMessage.value = 'Thiết bị không hỗ trợ quay video.'
    statusTone.value = 'error'
    return false
  }

  try {
    stopVideoStream()
    videoStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })

    if (videoPreviewEl.value) {
      videoPreviewEl.value.srcObject = videoStream
      videoPreviewEl.value.muted = true
      videoPreviewEl.value.controls = false
      await videoPreviewEl.value.play?.()
    }

    isVideoPreviewOn.value = true
    return true
  } catch (error) {
    console.error('[v0] Lỗi mở camera video:', error.message)
    statusMessage.value = 'Không thể mở camera để quay video.'
    statusTone.value = 'error'
    return false
  }
}

const startRecording = async () => {
  if (isRecording.value) return
  if (!window.MediaRecorder) {
    statusMessage.value = 'Trình duyệt không hỗ trợ quay video.'
    statusTone.value = 'error'
    return
  }

  resetVideoSelection()
  const ready = await startVideoPreview()
  if (!ready) return

  const mimeType = getSupportedMimeType()
  recordedChunks = []

  try {
    mediaRecorder = mimeType ? new MediaRecorder(videoStream, { mimeType }) : new MediaRecorder(videoStream)
  } catch (error) {
    console.error('[v0] Lỗi khởi tạo MediaRecorder:', error.message)
    statusMessage.value = 'Không thể bắt đầu quay video.'
    statusTone.value = 'error'
    return
  }

  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data)
    }
  }

  mediaRecorder.onstop = () => {
    const blobType = mimeType || 'video/webm'
    const blob = new Blob(recordedChunks, { type: blobType })
    const extension = blobType.includes('mp4') ? 'mp4' : 'webm'
    const file = new File([blob], `register_${Date.now()}.${extension}`, { type: blobType })
    setVideoSelection(file)
    stopVideoStream()
  }

  mediaRecorder.start()
  isRecording.value = true
  statusMessage.value = 'Đang quay video...'
  statusTone.value = 'neutral'
}

const stopRecording = () => {
  if (!isRecording.value || !mediaRecorder) return
  isRecording.value = false
  mediaRecorder.stop()
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

const handleVideoSelection = (event) => {
  if (isRecording.value) return

  const file = (event.target.files || [])[0]
  if (!file) return

  if (!file.type.startsWith('video/')) {
    statusMessage.value = 'Vui lòng chọn đúng định dạng video.'
    statusTone.value = 'error'
    return
  }

  stopVideoStream()
  setVideoSelection(file)
  statusMessage.value = ''
  statusTone.value = 'neutral'
}

const clearVideoSelection = () => {
  if (isRecording.value) return
  stopVideoStream()
  resetVideoSelection()
}

const handleSubmit = async () => {
  if (!studentId.value || !fullName.value) {
    statusMessage.value = 'Vui lòng nhập đủ mã và họ tên.'
    statusTone.value = 'error'
    return
  }

  if (registrationMode.value === 'images' && selectedImageCount.value < minimumImages) {
    statusMessage.value = `Cần ít nhất ${minimumImages} ảnh để đăng ký.`
    statusTone.value = 'error'
    return
  }

  if (registrationMode.value === 'video' && !videoFile.value) {
    statusMessage.value = 'Vui lòng quay hoặc chọn video để đăng ký.'
    statusTone.value = 'error'
    return
  }

  isSubmitting.value = true
  statusMessage.value = ''

  try {
    const payloadSchedules = schedules.value
      .filter(s => s.shifts.length > 0)
      .map(s => ({
        day_of_week: s.day_of_week,
        shifts: s.shifts.join(',')
      }))

    if (payloadSchedules.length === 0) {
      statusMessage.value = 'Vui lòng chọn ít nhất 1 ca học.'
      statusTone.value = 'error'
      isSubmitting.value = false
      return
    }

    if (registrationMode.value === 'images') {
      const imagesBase64 = await Promise.all(selectedImages.value.map((file) => fileToBase64(file)))

      const response = await registerEmployee({
        student_id: studentId.value,
        name: fullName.value,
        images_base64: imagesBase64,
      })

      // Đăng ký lịch học luôn
      try {
        await apiClient.post(`/schedule/${studentId.value}`, { schedules: payloadSchedules })
        statusMessage.value = `Đăng ký khuôn mặt thành công: ${response.name} (${response.accepted_images} ảnh hợp lệ). Đã lưu lịch học. Vui lòng chờ Giảng viên duyệt.`
        statusTone.value = 'success'
      } catch (err) {
        console.error("Lỗi đăng ký lịch", err)
        statusMessage.value = `Khuôn mặt đã lưu NHƯNG LƯU LỊCH THẤT BẠI: ${err?.response?.data?.detail || 'Lỗi hệ thống'}. Vui lòng ấn nút Gửi lại hoặc lưu ở tab Đăng ký Ca học.`
        statusTone.value = 'error'
      }
    } else {
      const response = await registerEmployeeVideo({
        student_id: studentId.value,
        name: fullName.value,
        videoFile: videoFile.value,
      })

      // Đăng ký lịch học luôn
      try {
        await apiClient.post(`/schedule/${studentId.value}`, { schedules: payloadSchedules })
        statusMessage.value = `Đăng ký khuôn mặt thành công: ${response.name} (${response.frames_processed} khung hình hợp lệ). Đã lưu lịch học. Vui lòng chờ Giảng viên duyệt.`
        statusTone.value = 'success'
      } catch (err) {
        console.error("Lỗi đăng ký lịch", err)
        statusMessage.value = `Khuôn mặt đã lưu NHƯNG LƯU LỊCH THẤT BẠI: ${err?.response?.data?.detail || 'Lỗi hệ thống'}. Vui lòng ấn nút Gửi lại hoặc lưu ở tab Đăng ký Ca học.`
        statusTone.value = 'error'
      }
    }
  } catch (error) {
    console.error('[v0] Lỗi đăng ký nhân sự:', error.message)
    const detail = error?.response?.data?.detail
    statusMessage.value = detail || 'Không thể kết nối hệ thống đăng ký. Vui lòng thử lại.'
    statusTone.value = 'error'
  } finally {
    isSubmitting.value = false
  }
}

watch(registrationMode, (mode) => {
  statusMessage.value = ''
  statusTone.value = 'neutral'

  if (mode === 'images') {
    stopVideoStream()
    resetVideoSelection()
  } else {
    clearPreviewItems()
    selectedImages.value = []
  }
})

onBeforeUnmount(() => {
  clearPreviewItems()
  stopVideoStream()
  resetVideoSelection()
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

.mode-toggle {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.mode-toggle label {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: #fff;
}

.mode-toggle label.active {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 1px rgba(67, 97, 238, 0.2);
}

.mode-toggle input {
  accent-color: var(--primary-color);
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

.video-panel {
  display: grid;
  gap: 10px;
}

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.video-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.secondary-btn,
.ghost-btn,
.file-btn {
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: #fff;
  color: var(--text-main);
}

.secondary-btn:disabled,
.ghost-btn:disabled,
.file-btn.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.file-btn input {
  display: none;
}

.ghost-btn {
  background: #f8fafc;
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

.video-preview {
  display: grid;
  gap: 12px;
  margin-top: 20px;
}

.video-preview-el {
  width: 100%;
  border-radius: 14px;
  border: 1px solid var(--border-color);
  background: #0f172a;
  max-height: 320px;
}

.video-meta {
  margin: 0;
  font-size: 12px;
  color: var(--text-sub);
  word-break: break-word;
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

.days-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.day-row {
  display: flex;
  align-items: center;
  background-color: #f8fafc;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}
.day-label {
  width: 90px;
  font-weight: 500;
  font-size: 13px;
}
.shifts {
  display: flex;
  gap: 12px;
}
.shift-checkbox {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  cursor: pointer;
  margin: 0 !important;
}
</style>