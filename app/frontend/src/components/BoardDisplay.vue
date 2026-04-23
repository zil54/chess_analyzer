<template>
  <div class="board-display" :style="appearanceVars">
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
    flipped: { type: Boolean, default: false },
    boardTheme: { type: Object, required: true },
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
  computed: {
    appearanceVars() {
      return {
        '--board-light': this.boardTheme?.light || '#f0d9b5',
        '--board-dark': this.boardTheme?.dark || '#b58863',
        '--coord-light': this.boardTheme?.coordLight || '#f0d9b5',
        '--coord-dark': this.boardTheme?.coordDark || '#946f51',
      };
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

.board-display :deep(cg-board) {
  background: conic-gradient(
    var(--board-dark) 25%,
    var(--board-light) 0 50%,
    var(--board-dark) 0 75%,
    var(--board-light) 0
  ) 0 0 / 25% 25% !important;
}

.board-display :deep(.orientation-white .files coord:nth-child(odd)),
.board-display :deep(.orientation-white .ranks coord:nth-child(2n)),
.board-display :deep(.orientation-black .files coord:nth-child(2n)),
.board-display :deep(.orientation-black .ranks coord:nth-child(odd)) {
  color: var(--coord-light) !important;
}

.board-display :deep(.orientation-white .files coord:nth-child(2n)),
.board-display :deep(.orientation-white .ranks coord:nth-child(odd)),
.board-display :deep(.orientation-black .files coord:nth-child(odd)),
.board-display :deep(.orientation-black .ranks coord:nth-child(2n)) {
  color: var(--coord-dark) !important;
}



.board-display :deep(.promotion-dialog) {
  background-color: var(--board-light);
  border-color: var(--board-dark);
}

:deep(.cg-wrap) {
  width: min(100%, 560px);
  aspect-ratio: 1 / 1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-radius: 4px;
}
</style>
