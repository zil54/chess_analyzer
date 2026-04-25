<template>
  <div class="fen-controls">
    <!-- FEN input hidden for now (eventually FEN will come from DB/PGN selection) -->
    <div class="fen-hidden" aria-hidden="true">
      <h2>Enter FEN:</h2>
      <input :value="fen" @input="$emit('update:fen', $event.target.value)" />
      <button @click="$emit('render-board')">Render</button>
    </div>

    <div class="toolbar" role="group" aria-label="Analyzer controls">
      <button
        type="button"
        class="icon-btn upload-btn"
        title="Upload PGN Database"
        aria-label="Upload PGN"
        @click="$emit('upload-pgn')"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" class="toolbar-icon" focusable="false">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
        </svg>
      </button>

      <button
        type="button"
        class="icon-btn analyze-btn analyze-bulb-btn"
        title="Analyze (SF18)"
        aria-label="Analyze with Stockfish 18"
        :disabled="!canAnalyze || !isFenValid || isAnalyzing"
        @click="$emit('start-analysis')"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" class="toolbar-icon toolbar-icon-bulb" focusable="false">
          <path d="M9 18h6" />
          <path d="M10 21h4" />
          <path d="M8 9a4 4 0 1 1 8 0c0 1.7-.83 2.67-1.86 3.92-.65.78-1.22 1.57-1.51 2.58h-1.26c-.29-1.01-.86-1.8-1.51-2.58C8.83 11.67 8 10.7 8 9Z" />
          <path d="M12 3v2" />
          <path d="M4.5 9h2" />
          <path d="M17.5 9h2" />
          <path d="m6.2 4.7 1.4 1.4" />
          <path d="m16.4 6.1 1.4-1.4" />
        </svg>
      </button>

      <button
        type="button"
        class="icon-btn stop-btn"
        title="Stop Analysis"
        aria-label="Stop Analysis"
        :disabled="!isAnalyzing"
        @click="$emit('stop-analysis')"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" class="toolbar-icon" focusable="false">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      </button>

      <button
        type="button"
        class="icon-btn flip-btn"
        title="Flip Board"
        aria-label="Flip Board"
        @click="$emit('flip-board')"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" class="toolbar-icon" focusable="false">
          <path d="M8 18V6M8 6L4 10M8 6L12 10M16 6V18M16 18L12 14M16 18L20 14" />
        </svg>
      </button>

      <button
        type="button"
        class="icon-btn settings-btn"
        title="Board Settings"
        aria-label="Board Settings"
        @click="$emit('open-board-settings')"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" class="toolbar-icon" focusable="false">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.61.82.33l-.06.06a2 2 0 0 1l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      </button>

      <button
        type="button"
        class="icon-btn future-btn"
        title="Quiz Mode (future)"
        aria-label="Quiz Mode"
        disabled
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" class="toolbar-icon" focusable="false">
          <circle cx="12" cy="12" r="10" />
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FenControls',
  props: {
    fen: { type: String, required: true },
    isFenValid: { type: Boolean, required: true },
    canAnalyze: { type: Boolean, required: true },
    isAnalyzing: { type: Boolean, required: true }
  },
  emits: ['update:fen', 'render-board', 'start-analysis', 'stop-analysis', 'upload-pgn', 'flip-board', 'open-board-settings']
};
</script>

<style scoped>
.fen-controls {
  display: flex;
  justify-content: center;
}

.fen-hidden {
  display: none;
}

.toolbar {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 6px;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid #d8dee4;
  border-radius: 99px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}

.icon-btn {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  border-radius: 999px;
  font-size: 15px;
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease, background-color 0.12s ease;
}

.toolbar-icon {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.toolbar-icon-bulb {
  width: 18px;
  height: 18px;
  overflow: visible;
}

.toolbar-icon-bulb path {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.35;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.icon-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.14);
}

.icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  box-shadow: none;
}

.upload-btn {
  background: #dcfce7;
  color: #15803d;
}

.analyze-btn {
  background: #dbeafe;
  color: #1d4ed8;
}

.stop-btn {
  background: #fee2e2;
  color: #b91c1c;
}

.flip-btn {
  background: #ede9fe;
  color: #6d28d9;
}

.settings-btn {
  background: #fff7ed;
  color: #c2410c;
}

.future-btn {
  background: #f1f5f9;
  color: #94a3b8;
  cursor: not-allowed;
}
</style>
