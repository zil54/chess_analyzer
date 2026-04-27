<template>
  <div class="pgn-panel">
    <div v-if="pgnData" class="pgn-header">
      <h3>{{ pgnData.headers.white }} vs {{ pgnData.headers.black }}</h3>
      <p>{{ pgnData.headers.event }} - {{ pgnData.headers.date }}</p>
      <p>Result: {{ pgnData.headers.result }}</p>
    </div>

    <div v-if="pgnData" class="notes-section">
      <div v-if="currentTreeNode && (currentTreeNode.san || currentTreeNode.id === 0 || currentTreeNode.ply === 0)" class="notes-active">
        <div class="notes-header-row">
          <label>{{ moveLabel }} - Comment:</label>
          <div class="notes-actions">
            <button type="button" class="annotations-toggle" @click="toggleNagPopover">
              {{ isNagPopoverOpen ? 'Hide Annotations' : 'Annotations' }}
            </button>
          </div>
        </div>

        <div v-if="isNagPopoverOpen" class="nag-popover">
          <div class="nag-popover-header">
            <span class="nag-popover-title">NAG Palette</span>
            <button type="button" class="nag-popover-close" @click="closeNagPopover">×</button>
          </div>

          <div class="nag-group">
            <div class="nag-group-label">Quality</div>
            <div class="nag-buttons">
              <button
                v-for="[nag, symbol, title] in qualityNags"
                :key="`quality-${nag}`"
                type="button"
                class="nag-btn"
                :class="{ active: hasNag(nag) }"
                :title="title"
                @click="toggleNag(nag)"
              >
                {{ symbol }}
              </button>
            </div>
          </div>

          <div class="nag-group">
            <div class="nag-group-label">Position</div>
            <div class="nag-buttons">
              <button
                v-for="[nag, symbol, title] in positionNags"
                :key="`position-${nag}`"
                type="button"
                class="nag-btn"
                :class="{ active: hasNag(nag) }"
                :title="title"
                @click="toggleNag(nag)"
              >
                {{ symbol }}
              </button>
            </div>
          </div>

          <div class="nag-group">
            <div class="nag-group-label">Mixed</div>
            <div class="nag-buttons">
              <button
                v-for="[nag, symbol, title] in mixedNags"
                :key="`mixed-${nag}`"
                type="button"
                class="nag-btn"
                :class="{ active: hasNag(nag) }"
                :title="title"
                @click="toggleNag(nag)"
              >
                {{ symbol }}
              </button>
            </div>
          </div>

          <div class="nag-group">
            <div class="nag-group-label">Special</div>
            <div class="nag-buttons">
              <button
                v-for="[nag, symbol, title] in specialNags"
                :key="`special-${nag}`"
                type="button"
                class="nag-btn"
                :class="{ active: hasNag(nag) }"
                :title="title"
                @click="toggleNag(nag)"
              >
                {{ symbol }}
              </button>
            </div>
          </div>

          <div class="nag-popover-actions">
            <button type="button" class="nag-popover-action nag-popover-clear" @click="clearNags">Clear</button>
            <button type="button" class="nag-popover-action" @click="closeNagPopover">Done</button>
          </div>
        </div>

        <textarea
          v-model="commentText"
          @input="updateComment"
          placeholder="Add a comment for this move..."
          class="comment-input"
        ></textarea>
      </div>

      <div v-else class="notes-empty">
        <p>Select a move or the starting position to edit its comment and annotations.</p>
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
  emits: ['update-node-comment', 'update-node-nags'],
  data() {
    return {
      commentText: '',
      isNagPopoverOpen: false,
      selectedNags: new Set(),
      qualityNags: [
        [1, '!', 'Good move'],
        [2, '?', 'Bad move'],
        [3, '!!', 'Excellent move'],
        [4, '??', 'Blunder'],
        [5, '!?', 'Interesting move'],
        [6, '?!', 'Dubious move']
      ],
      positionNags: [
        [10, '=', 'Equal position'],
        [14, '+=', 'Slightly better for White'],
        [15, '=+', 'Slightly better for Black'],
        [16, '+/-', 'Better for White'],
        [17, '-/+', 'Better for Black'],
        [18, '+-', 'Winning for White'],
        [19, '-+', 'Winning for Black']
      ],
      mixedNags: [
        [22, '+/−', 'Advantage over Disadvantage'],
        [23, '−/+', 'Disadvantage over Advantage'],
        [131, '+/=', 'White compensation'],
        [133, '=/+', 'Black compensation']
      ],
      specialNags: [
        [12, '∞', 'Unclear position'],
        [130, 'Z', 'Zugzwang'],
        [138, '⇄', 'Counterplay'],
        [32, '⟳', 'Repetition'],
        [36, '↑', 'Initiative'],
        [40, '→', 'Attack']
      ]
    };
  },
  watch: {
    currentTreeNode: {
      handler(newNode) {
        if (newNode && (newNode.san || newNode.id === 0 || newNode.ply === 0)) {
          this.commentText = newNode.comment || '';
          this.selectedNags = new Set(Array.isArray(newNode.nags) ? newNode.nags : []);
        } else {
          this.commentText = '';
          this.selectedNags = new Set();
        }
        this.isNagPopoverOpen = false;
      },
      immediate: true,
      deep: true
    }
  },
  computed: {
    moveLabel() {
      if (!this.currentTreeNode) return 'Move';
      // If root node (starting position)
      if (this.currentTreeNode.id === 0 || this.currentTreeNode.ply === 0) {
        return 'Starting Position';
      }
      // If regular move
      if (this.currentTreeNode.san) {
        const moveNum = this.currentTreeNode.move_number || '';
        const color = this.currentTreeNode.color;
        const san = this.currentTreeNode.san;
        if (color === 'w') {
          return `${moveNum}. ${san}`;
        }
        return `${moveNum}... ${san}`;
      }
      return 'Move';
    }
  },
  methods: {
    updateComment() {
      if (!this.currentTreeNode || !this.currentTreeNode.id) return;
      this.$emit('update-node-comment', {
        nodeId: this.currentTreeNode.id,
        comment: this.commentText
      });
    },
    toggleNagPopover() {
      if (!this.currentTreeNode?.id) return;
      this.isNagPopoverOpen = !this.isNagPopoverOpen;
    },
    closeNagPopover() {
      this.isNagPopoverOpen = false;
    },
    hasNag(nag) {
      return this.selectedNags.has(nag);
    },
    toggleNag(nag) {
      if (!this.currentTreeNode?.id) return;
      const next = new Set(this.selectedNags);
      if (next.has(nag)) {
        next.delete(nag);
      } else {
        next.add(nag);
      }
      this.selectedNags = next;
      this.emitNags();
    },
    clearNags() {
      if (!this.currentTreeNode?.id) return;
      this.selectedNags = new Set();
      this.emitNags();
    },
    emitNags() {
      this.$emit('update-node-nags', {
        nodeId: this.currentTreeNode.id,
        nags: Array.from(this.selectedNags)
      });
    }
  }
};
</script>

<style scoped>
.pgn-panel {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pgn-header {
  margin: 0;
  padding: 8px;
  background-color: #f0f7ff;
  border-left: 3px solid #2196F3;
  border-radius: 4px;
  font-size: 0.85rem;
}

.pgn-header h3 {
  margin: 0 0 4px 0;
  font-size: 0.95rem;
  color: #1976D2;
  font-weight: 600;
}

.pgn-header p {
  margin: 2px 0;
  font-size: 0.8rem;
  color: #555;
}

.notes-section {
  padding: 8px;
  background-color: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.notes-active {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notes-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.notes-header-row label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #2c3e50;
}

.notes-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.annotations-toggle {
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #f8fafc;
  color: #1e3a8a;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
}

.annotations-toggle:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

.nag-popover {
  padding: 10px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.1);
}

.nag-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.nag-popover-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: #1f2937;
}

.nag-popover-close {
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.nag-group {
  margin-bottom: 8px;
}

.nag-group:last-of-type {
  margin-bottom: 10px;
}

.nag-group-label {
  margin-bottom: 4px;
  font-size: 10px;
  font-weight: 700;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.nag-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.nag-btn {
  min-width: 34px;
  padding: 4px 6px;
  border: 1px solid #d0d7de;
  border-radius: 4px;
  background: #f8fafc;
  color: #1f2937;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}

.nag-btn:hover,
.nag-btn.active {
  background: #dbeafe;
  border-color: #60a5fa;
  color: #1d4ed8;
}

.nag-popover-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.nag-popover-action {
  padding: 5px 8px;
  border: 1px solid #d0d7de;
  border-radius: 4px;
  background: #f8fafc;
  color: #1f2937;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.nag-popover-action:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

.nag-popover-clear {
  color: #b91c1c;
}

.comment-input {
  padding: 6px;
  font-size: 0.85rem;
  border: 1px solid #d0d0d0;
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
  min-height: 70px;
  max-height: 150px;
  color: #2c3e50;
}

.comment-input:focus {
  outline: none;
  border-color: #2196F3;
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
}

.comment-input::placeholder {
  color: #bbb;
}

.notes-empty p {
  margin: 0;
  color: #6b7280;
  font-size: 0.82rem;
  font-style: italic;
}
</style>
