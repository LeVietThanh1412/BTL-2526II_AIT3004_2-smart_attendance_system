<template>
  <div class="login-container">
    <div class="login-card">
      <h2>Admin Login</h2>
      <p>Đăng nhập bằng tài khoản Giảng viên</p>
      
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label>Tên đăng nhập</label>
          <input type="text" v-model="username" required placeholder="Nhập tên đăng nhập" />
        </div>
        
        <div class="form-group">
          <label>Mật khẩu</label>
          <input type="password" v-model="password" required placeholder="Nhập mật khẩu" />
        </div>
        
        <div v-if="errorMsg" class="error-msg">
          {{ errorMsg }}
        </div>
        
        <button type="submit" class="btn-submit" :disabled="isLoading">
          <span v-if="isLoading">Đang đăng nhập...</span>
          <span v-else>Đăng Nhập</span>
        </button>

        <div style="margin-top: 15px; text-align: center;">
          <router-link to="/checkin" style="color: #3b82f6; text-decoration: none; font-size: 0.875rem;">
            ← Quay về trang điểm danh
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { loginAdmin } from '../../shared/api'

const router = useRouter()
const username = ref('')
const password = ref('')
const errorMsg = ref('')
const isLoading = ref(false)

const handleLogin = async () => {
  if (!username.value || !password.value) return
  
  isLoading.value = true
  errorMsg.value = ''
  
  try {
    const data = await loginAdmin(username.value, password.value)
    if (data && data.token) {
      localStorage.setItem('adminToken', data.token)
      router.push('/admin/dashboard')
    }
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Sai tài khoản hoặc mật khẩu.'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: #f1f5f9;
}

.login-card {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  width: 100%;
  max-width: 400px;
}

.login-card h2 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: #1e293b;
  text-align: center;
}

.login-card p {
  color: #64748b;
  text-align: center;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #334155;
  font-size: 0.875rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  outline: none;
  font-size: 1rem;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-group input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.error-msg {
  color: #ef4444;
  font-size: 0.875rem;
  margin-bottom: 1rem;
  text-align: center;
}

.btn-submit {
  width: 100%;
  padding: 0.75rem;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-submit:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
