<template>
  <div class="board-display">
    <TheChessboard
      :board-config="boardConfig"
      :reactive-config="true"
      player-color="both"
      @board-created="onBoardCreated"
      @move="handleMove"
    />
  </div>
</template>

<script>
import { TheChessboard } from 'vue3-chessboard';
import 'vue3-chessboard/style.css';

export default {
  name: 'BoardDisplay',
  components: {
    TheChessboard
  },
  props: {
    fen: { type: String, required: true },
    flipped: { type: Boolean, default: false }
  },
  data() {
    return {
      boardApi: null,
      boardConfig: {
        fen: this.fen,
        orientation: this.flipped ? 'black' : 'white',
        coordinates: true,
        animation: {
          enabled: true,
          duration: 100
        },
        movable: {
          color: 'both',
          free: false
        }
      }
    };
  },
  watch: {
    fen(newFen) {
      // Update FEN in board config carefully to avoid resetting board
      this.boardConfig.fen = newFen;
    },
    flipped(newVal) {
      this.boardConfig.orientation = newVal ? 'black' : 'white';
      if (this.boardApi && typeof this.boardApi.toggleOrientation === 'function') {
        this.boardApi.toggleOrientation();
      }
    }
  },
  methods: {
    onBoardCreated(api) {
      this.boardApi = api;
      if (this.fen) {
        this.boardApi.setPosition(this.fen);
      }
    },
    handleMove(moveInfo) {
      if (moveInfo) {
        const moveFen = (this.boardApi && this.boardApi.game)
            ? this.boardApi.game.fen()
            : (moveInfo.after || "");

        this.$emit('user-move', {
          ...moveInfo,
          fen: moveFen
        });
      }
    }
  }
};
</script>

<style scoped>
.board-display {
  width: 100%;
  display: flex;
  justify-content: center;
}

:deep(.cg-wrap) {
  width: min(100%, 560px);
  aspect-ratio: 1 / 1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-radius: 4px;
}
</style>
