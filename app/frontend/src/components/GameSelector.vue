<template>
  <div class="game-selector" v-if="games && games.length > 0">
    <div class="selector-header">
      <h3>📂 Games ({{ games.length }})</h3>
    </div>
    <div class="games-list">
      <div
        v-for="game in games"
        :key="game.id"
        class="game-item"
        :class="{ active: activeGameId === game.id }"
        @click="selectGame(game.id)"
      >
        <div class="game-title">
          <strong>{{ game.white }} vs {{ game.black }}</strong>
          <div class="game-title-right">
            <span v-if="activeGameId === game.id" class="displayed-badge">Displayed in PGN</span>
            <span class="game-result">{{ game.result }}</span>
          </div>
        </div>
        <div class="game-meta">
          <span class="event">{{ game.event }}</span>
          <span class="date">{{ game.date }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GameSelector',
  props: {
    games: {
      type: Array,
      required: true,
      default: () => []
    },
    initialGameId: {
      type: [Number, String],
      default: null
    },
    displayedGameId: {
      type: [Number, String],
      default: null
    }
  },
  computed: {
    activeGameId() {
      return this.displayedGameId ?? this.initialGameId;
    }
  },
  methods: {
    selectGame(gameId) {
      this.$emit('select-game', gameId);
    }
  }
};
</script>

<style scoped>
.game-selector {
  margin-bottom: 0.75rem;
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
  border: 1px solid #ddd;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.selector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.selector-header h3 {
  margin: 0;
  font-size: 0.9rem;
  color: #333;
}

.games-list {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  max-height: 180px;
  overflow-y: auto;
  border: 1px solid #ccc;
  border-radius: 3px;
  background: white;
  padding: 0.4rem;
}

.game-item {
  padding: 0.4rem;
  border-radius: 3px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: all 0.2s ease;
  background: #fafafa;
}

.game-item:hover {
  background: #e8f4f8;
  border-left-color: #3498db;
}

.game-item.active {
  background: #d4edfa;
  border-left-color: #2980b9;
  font-weight: 500;
}

.game-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}

.game-title strong {
  flex: 1;
  font-size: 0.8rem;
  color: #2c3e50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.game-result {
  font-size: 0.7rem;
  padding: 0.2rem 0.3rem;
  background: #e0e0e0;
  border-radius: 2px;
  white-space: nowrap;
}

.game-title-right {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.displayed-badge {
  font-size: 0.62rem;
  font-weight: 600;
  color: #0c4f7a;
  background: #e7f4ff;
  border: 1px solid #9ecdf1;
  border-radius: 10px;
  padding: 0.12rem 0.4rem;
  white-space: nowrap;
}

.game-meta {
  display: flex;
  gap: 0.5rem;
  font-size: 0.7rem;
  color: #666;
}

.event {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.date {
  white-space: nowrap;
}

/* Scrollbar styling */
.games-list::-webkit-scrollbar {
  width: 6px;
}

.games-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.games-list::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 3px;
}

.games-list::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>


