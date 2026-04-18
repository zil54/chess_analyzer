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
  margin: 0 0 8px;
  padding: 8px 10px;
  background-color: #f0f7ff;
  border-left: 3px solid #2196F3;
  border-radius: 4px;
  font-size: 0.9rem;
}

.pgn-header h3 {
  margin: 0 0 4px 0;
  font-size: 0.95rem;
  color: #1976D2;
  font-weight: 600;
}

.pgn-header p {
  margin: 3px 0;
  font-size: 0.85rem;
  color: #555;
}

.current-move {
  margin-top: 4px;
  font-size: 0.9rem;
  color: #2c3e50;
}

.variation-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 6px;
  border-radius: 3px;
  background: #fff4e5;
  color: #9a6700;
  font-size: 0.75rem;
  font-weight: 600;
}
</style>
