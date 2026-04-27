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
import { Chess } from 'chess.js';
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
    allowFreeEdit: { type: Boolean, default: true }
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
          duration: 50
        },
        movable: {
          color: 'both',
          free: this.allowFreeEdit,
          dests: this.allowFreeEdit ? {} : this.calculateDests(this.fen)
        }
      }
    };
  },
   watch: {
    fen(newFen) {
      if (!newFen) return;

      const nextDests = this.allowFreeEdit ? {} : this.calculateDests(newFen);

      // Update the config object to maintain sync with reactive-config
      this.boardConfig.fen = newFen;
      this.boardConfig.movable.dests = nextDests;
      this.boardConfig.movable.free = this.allowFreeEdit;

      // Actually update the board position via the API
      if (this.boardApi && typeof this.boardApi.setPosition === 'function') {
        this.boardApi.setPosition(newFen);

        // Force a complete state reset to clear any stale drag-drop state
        // This is critical after each move to avoid the "can't move after first move" bug
        if (typeof this.boardApi.set === 'function') {
          // First, reset the board state completely
          this.boardApi.set({
            fen: newFen,
            movable: {
              color: 'both',
              free: this.allowFreeEdit,
              dests: nextDests
            },
            selection: {
              enabled: true
            }
          });
        }

        // Give the board a chance to process the new state
        this.$nextTick(() => {
          // Then recalculate dests one more time to ensure they're correct
          const finalDests = this.allowFreeEdit ? {} : this.calculateDests(newFen);
          if (typeof this.boardApi.set === 'function') {
            this.boardApi.set({
              movable: {
                color: 'both',
                free: this.allowFreeEdit,
                dests: finalDests
              }
            });
          }
        });
      }
    },
    allowFreeEdit(newVal) {
      // When mode switches (e.g., PGN loaded/unloaded), update movable config
      this.boardConfig.movable.free = newVal;
      const nextDests = newVal ? {} : this.calculateDests(this.fen);
      this.boardConfig.movable.dests = nextDests;
      if (this.boardApi && typeof this.boardApi.set === 'function') {
        this.boardApi.set({
          movable: {
            color: 'both',
            free: newVal,
            dests: nextDests
          }
        });
      }
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
    calculateDests(fen) {
      try {
        const chess = new Chess(fen);
        const dests = {};
        for (const move of chess.moves({ verbose: true })) {
          const from = move.from;
          const to = move.to;
          if (!dests[from]) dests[from] = [];
          dests[from].push(to);
        }
        return dests;
      } catch (_) {
        return {};
      }
    },
    onBoardCreated(api) {
       this.boardApi = api;
       if (this.fen) {
         this.boardApi.setPosition(this.fen);
       }
       // Ensure movable is set to both sides from the start
       const initialDests = this.allowFreeEdit ? {} : this.calculateDests(this.fen);
       this.boardConfig.movable.dests = initialDests;
       this.boardConfig.movable.free = this.allowFreeEdit;

       // Initialize with all necessary state to enable drag-drop
       if (typeof this.boardApi.set === 'function') {
         this.boardApi.set({
           fen: this.fen,
           movable: {
             color: 'both',
             free: this.allowFreeEdit,
             dests: initialDests
           },
           draggable: {
             enabled: true,
             showGhost: true,
             distance: 3
           },
           selectable: {
             enabled: true
           },
           selection: {
             enabled: true
           }
         });
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

         // Force a re-sync of the board state after the move is processed
         // This ensures drag-drop handlers are properly reset for the next move
         this.$nextTick(() => {
           this.resetMovableState();
         });
       }
     },

     resetMovableState() {
       // Force complete reset of movable state to prevent "stuck after first move" bug
       if (this.boardApi && typeof this.boardApi.set === 'function') {
         const currentFen = this.boardApi.game?.fen?.() || this.fen;
         const nextDests = this.allowFreeEdit ? {} : this.calculateDests(currentFen);

         this.boardApi.set({
           movable: {
             color: 'both',
             free: this.allowFreeEdit,
             dests: nextDests
           },
           selection: {
             enabled: true
           }
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
