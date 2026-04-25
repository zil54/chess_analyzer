<template>
  <div class="board-settings-panel">
    <div class="panel-header">
      <div>
        <h3>Board Settings</h3>
        <p>Choose a board palette.</p>
      </div>
      <button type="button" class="close-btn" aria-label="Close board settings" @click="$emit('close')">×</button>
    </div>

    <section class="settings-section">
      <div class="section-title">Board Colors</div>
      <div class="theme-grid">
        <button
          v-for="theme in boardThemes"
          :key="theme.id"
          type="button"
          class="theme-card"
          :class="{ selected: selectedBoardThemeId === theme.id }"
          @click="$emit('select-board-theme', theme.id)"
        >
          <span class="board-swatch" :style="boardSwatchStyle(theme)"></span>
          <span class="theme-label">{{ theme.label }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<script>
export default {
  name: 'BoardSettingsPanel',
  props: {
    boardThemes: { type: Array, required: true },
    selectedBoardThemeId: { type: String, required: true },
  },
  emits: ['close', 'select-board-theme'],
  methods: {
    boardSwatchStyle(theme) {
      return {
        background: `conic-gradient(${theme.dark} 25%, ${theme.light} 0 50%, ${theme.dark} 0 75%, ${theme.light} 0) 0 0 / 50% 50%`,
      };
    },
  },
};
</script>

<style scoped>
.board-settings-panel {
  width: min(360px, 80vw);
  padding: 14px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #d8dee4;
  border-radius: 14px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.16);
  text-align: left;
  backdrop-filter: blur(8px);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.panel-header h3 {
  margin: 0;
  font-size: 1rem;
  color: #111827;
}

.panel-header p {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: #6b7280;
}

.close-btn {
  margin: 0;
  padding: 0;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.close-btn:hover {
  background: #e2e8f0;
}

.settings-section + .settings-section {
  margin-top: 14px;
}

.section-title {
  margin-bottom: 8px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #475569;
  text-transform: uppercase;
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.theme-card {
  margin: 0;
  padding: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.12s ease, box-shadow 0.12s ease, transform 0.12s ease;
}

.theme-card:hover {
  transform: translateY(-1px);
  border-color: #93c5fd;
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.12);
}

.theme-card.selected {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.board-swatch {
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.12);
}

.theme-label {
  font-size: 0.84rem;
  font-weight: 600;
  color: #1f2937;
}

@media (max-width: 640px) {
  .board-settings-panel {
    width: min(94vw, 420px);
  }

  .theme-grid {
    grid-template-columns: 1fr;
  }
}
</style>








