<template>
  <div class="language-switcher">
    <button 
      v-for="locale in availableLocales" 
      :key="locale.key"
      class="lang-btn"
      :class="{ active: currentLocale === locale.key }"
      @click="changeLocale(locale.key)"
    >
      {{ locale.label }}
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { availableLocales } from '../i18n'

const { locale } = useI18n()

const currentLocale = computed(() => locale.value)

const changeLocale = (newLocale) => {
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
  
  // Update HTML lang attribute
  document.documentElement.lang = newLocale
  
  // Optional: Reload page to ensure all components pick up the new locale
  // window.location.reload()
}
</script>

<style scoped>
.language-switcher {
  display: flex;
  gap: 4px;
  align-items: center;
}

.lang-btn {
  padding: 4px 10px;
  border: 1px solid #E5E5E5;
  background: transparent;
  color: #666;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 3px;
}

.lang-btn:hover {
  border-color: #999;
  color: #333;
}

.lang-btn.active {
  background: #000;
  color: #FFF;
  border-color: #000;
}
</style>
