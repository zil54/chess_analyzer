<template>
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
</template>

<script>
export default {
  name: 'PgnMovesList',
  props: {
    pgnData: { type: Object, default: null },
    currentMove: { type: Number, required: true },
  },
  emits: ['select-move'],
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
  }
};
</script>

<style scoped>
.moves-list {
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
</style>

