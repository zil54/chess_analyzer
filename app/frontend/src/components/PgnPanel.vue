<template>
  <div class="pgn-panel">
    <h1>PGN Upload</h1>
    <button class="pgn-upload-btn" @click="$emit('upload-pgn')">Upload PGN File</button>

    <div v-if="pgnData" class="pgn-info">
      <h3>{{ pgnData.headers.white }} vs {{ pgnData.headers.black }}</h3>
      <p>{{ pgnData.headers.event }} - {{ pgnData.headers.date }}</p>
      <p>Result: {{ pgnData.headers.result }}</p>
      <div class="move-controls">
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
      <div v-if="currentPosition" class="current-move">
        <strong v-if="currentPosition.san">{{ currentPosition.san }}</strong>
        <span v-else>Starting position</span>
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

/* Styles largely rely on parent; specific tweaks can go here if needed. */
</style>
