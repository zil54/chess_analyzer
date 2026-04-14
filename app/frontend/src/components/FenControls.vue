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
        title="Upload PGN"
        aria-label="Upload PGN"
        @click="$emit('upload-pgn')"
      >
        <span aria-hidden="true">⤴</span>
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
        title="Stop"
        aria-label="Stop"
        :disabled="!isAnalyzing"
        @click="$emit('stop-analysis')"
      >
        <span aria-hidden="true">⏹</span>
      </button>

      <button
        type="button"
        class="icon-btn flip-btn"
        title="Flip Board"
        aria-label="Flip Board"
        @click="$emit('flip-board')"
      >
        <span aria-hidden="true">↻</span>
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
  emits: ['update:fen', 'render-board', 'start-analysis', 'stop-analysis', 'upload-pgn', 'flip-board']
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
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 6px 10px;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid #d8dee4;
  border-radius: 999px;
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
</style>
