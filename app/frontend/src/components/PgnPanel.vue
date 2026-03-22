  },
  computed: {
    moveRows() {
      const positions = Array.isArray(this.pgnData?.positions) ? this.pgnData.positions : [];
      const rows = [];

      for (let ply = 1; ply < positions.length; ply += 2) {
        const white = positions[ply];
        const black = positions[ply + 1] || null;
        if (!white?.san) {
          continue;
        }

        rows.push({
          moveNumber: Math.floor((ply + 1) / 2),
          white: {
            ply,
            san: white.san,
          },
          black: black?.san ? {
            ply: ply + 1,
            san: black.san,
          } : null,
        });
      }

      return rows;
    }

      <div v-if="moveRows.length" class="moves-list">
        <div class="moves-list-title">Game moves</div>
        <div class="moves-grid">
          <div
            v-for="row in moveRows"
            :key="`move-row-${row.moveNumber}`"
            class="moves-row"
          >
            <span class="move-number">{{ row.moveNumber }}.</span>
            <button
              type="button"
              class="move-chip"
              :class="{ active: currentMove === row.white.ply }"
              @click="$emit('select-move', row.white.ply)"
            >
              {{ row.white.san }}
            </button>
            <button
              v-if="row.black"
              type="button"
              class="move-chip"
              :class="{ active: currentMove === row.black.ply }"
              @click="$emit('select-move', row.black.ply)"
            >
              {{ row.black.san }}
            </button>
            <span v-else class="move-chip move-chip-placeholder" />
          </div>
        </div>
      </div>
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
        <span>Ply {{ currentMove }}/{{ pgnData.total_moves }}</span>
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
.moves-list {
  margin-top: 12px;
  padding: 10px 12px;
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

.moves-list-title {
  margin-bottom: 8px;
  font-weight: 600;
  color: #2c3e50;
}

.moves-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
}

.moves-row {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) minmax(0, 1fr);
  gap: 8px;
  align-items: center;
}

.move-number {
  font-weight: 600;
  color: #2c3e50;
}

.move-chip {
  padding: 6px 10px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #fff;
  color: #1f2328;
  text-align: left;
  cursor: pointer;
}

.move-chip:hover {
  background: #eef6ff;
  border-color: #7ab7ff;
}

.move-chip.active {
  background: #dbeafe;
  border-color: #2563eb;
  color: #1d4ed8;
  font-weight: 600;
}

.move-chip-placeholder {
  visibility: hidden;
  pointer-events: none;
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
