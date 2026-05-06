// =====================================================================
// main.js - Entry point của ứng dụng Vue 3
// =====================================================================
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './shared/styles.css'

const app = createApp(App)
app.use(router)
app.mount('#app')
