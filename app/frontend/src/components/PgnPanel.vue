<template>
  <div class="pgn-panel">
    <div v-if="pgnData" class="pgn-header">
      <h3>{{ pgnData.headers.white }} vs {{ pgnData.headers.black }}</h3>
      <p>{{ pgnData.headers.event }} - {{ pgnData.headers.date }}</p>
      <p>Result: {{ pgnData.headers.result }}</p>
      <div v-if="currentPosition" class="current-move">
        <strong v-if="currentPosition.san">{{ currentPosition.san }}</strong>
        <span v-else>Starting position</span>
      </div>
    </div>

    <div class="pgn-controls">
      <button class="pgn-upload-btn" @click="$emit('upload-pgn')">Upload PGN File</button>

      <div v-if="pgnData" class="move-controls">
        <button @click="$emit('go-first')" :disabled="currentMove === 0">⏮ First</button>
        <button @click="$emit('go-prev')" :disabled="currentMove === 0">◀ Prev</button>
        <span>Move {{ currentMove }} / {{ pgnData.total_moves }}</span>
        <button
          @click="$emit('go-next')"
          :disabled="currentMove === pgnData.total_moves"
        >
          Next ▶
        </button>
        <button
          @click="$emit('go-last')"
          :disabled="currentMove === pgnData.total_moves"
        >
          Last ⏭
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PgnPanel',
  props: {
    pgnData: { type: Object, default: null },
    currentMove: { type: Number, required: true },
    currentPosition: { type: Object, default: null }
  }
};
</script>

<style scoped>
.pgn-panel {
  margin-top: 8px;
}

.pgn-header {
  margin: 0 0 10px;
  padding: 10px 12px;
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

.pgn-controls {
  margin-top: 10px;
}

.pgn-upload-btn {
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin: 5px 0;
}
.pgn-upload-btn:hover {
  background-color: #45a049;
}

.move-controls {
  margin: 10px 0 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.current-move {
  margin-top: 6px;
  font-size: 16px;
  color: #2c3e50;
}
</style>
