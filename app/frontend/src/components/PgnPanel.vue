<template>
  <div class="pgn-panel">
    <div v-if="pgnData" class="pgn-header">
      <h3>{{ pgnData.headers.white }} vs {{ pgnData.headers.black }}</h3>
      <p>{{ pgnData.headers.event }} - {{ pgnData.headers.date }}</p>
      <p>Result: {{ pgnData.headers.result }}</p>
      <div v-if="currentPosition" class="current-move">
        <strong v-if="currentPosition.san">{{ currentPosition.san }}</strong>
        <span v-else>Starting position</span>
        <span v-if="isVariationView" class="variation-badge">Viewing variation</span>
      </div>
    </div>

    <div v-if="pgnData" class="pgn-controls">
      <div class="move-controls">
        <button @click="$emit('go-first')" :disabled="currentMove === 0">⏮ First</button>
        <button @click="$emit('go-prev')" :disabled="!canGoPrev">◀ Prev</button>
        <span>Ply {{ currentPly }} / {{ pgnData.total_moves }}</span>
        <button
          @click="$emit('go-next')"
          :disabled="!canGoNext"
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
    currentPosition: { type: Object, default: null },
    currentTreeNode: { type: Object, default: null },
    canGoPrev: { type: Boolean, default: false },
    canGoNext: { type: Boolean, default: false }
  },
  computed: {
    isVariationView() {
      return Boolean(this.currentTreeNode?.san) && this.currentTreeNode?.is_mainline === false;
    },
    currentPly() {
      if (Number.isInteger(this.currentTreeNode?.ply)) {
        return this.currentTreeNode.ply;
      }
      if (Number.isInteger(this.currentPosition?.ply)) {
        return this.currentPosition.ply;
      }
      return this.currentMove;
    }
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

.move-controls {
  margin: 0;
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

.variation-badge {
  display: inline-block;
  margin-left: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #fff4e5;
  color: #9a6700;
  font-size: 12px;
  font-weight: 600;
}
</style>
