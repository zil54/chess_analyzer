<template>
  <div class="board-display">
    <TheChessboard
      :board-config="boardConfig"
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
      boardApi: null
    };
  },
  computed: {
    boardConfig() {
      return {
        fen: this.fen,
        orientation: this.flipped ? 'black' : 'white',
        coordinates: true,
        animation: {
          enabled: true,
          duration: 200
        }
      };
    }
  },
  watch: {
    fen(newFen) {
      if (this.boardApi && newFen) {
        try {
          const currentBoardFen = typeof this.boardApi.getFen === 'function'
            ? this.boardApi.getFen()
            : (this.boardApi.game ? this.boardApi.game.fen() : "");

          if (currentBoardFen !== newFen) {
            this.boardApi.setPosition(newFen);
          }
        } catch (err) {
          console.warn("Invalid FEN passed to boardApi", err);
        }
      }
    },
    flipped(newVal) {
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
        // ensure we reliably inject the fen string
        const moveFen = moveInfo.after ||
                        (typeof this.boardApi.getFen === 'function' ? this.boardApi.getFen() : null) ||
                        (this.boardApi.game ? this.boardApi.game.fen() : null);

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
