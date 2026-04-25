<template>
  <div class="game-notes">
    <div v-if="currentTreeNode && currentTreeNode.san" class="notes-content">
      <div class="selected-move-header">
        <h3>{{ moveLabel }}</h3>
        <p class="move-fen" v-if="currentTreeNode.fen">Position</p>
      </div>

      <!-- NAG Palette -->
      <div class="nag-section">
        <h4>Annotations</h4>
        <div class="palette-grid">
          <!-- Move Quality -->
          <div class="nag-group">
            <div class="group-label">Quality</div>
            <div class="nag-buttons">
              <button
                v-for="[nag, symbol, title] in qualityNags"
                :key="nag"
                @click="toggleNag(nag)"
                :title="title"
                class="nag-btn"
                :class="{ active: hasNag(nag) }"
              >
                {{ symbol }}
              </button>
            </div>
          </div>

          <!-- Position Assessment -->
          <div class="nag-group">
            <div class="group-label">Position</div>
            <div class="nag-buttons">
              <button
                v-for="[nag, symbol, title] in positionNags"
                :key="nag"
                @click="toggleNag(nag)"
                :title="title"
                class="nag-btn"
                :class="{ active: hasNag(nag) }"
              >
                {{ symbol }}
              </button>
            </div>
          </div>

          <!-- Mixed -->
          <div class="nag-group">
            <div class="group-label">Mixed</div>
            <div class="nag-buttons">
              <button
                v-for="[nag, symbol, title] in mixedNags"
                :key="nag"
                @click="toggleNag(nag)"
                :title="title"
                class="nag-btn"
                :class="{ active: hasNag(nag) }"
              >
                {{ symbol }}
              </button>
            </div>
          </div>

          <!-- Special -->
          <div class="nag-group">
            <div class="group-label">Special</div>
            <div class="nag-buttons">
              <button
                v-for="[nag, symbol, title] in specialNags"
                :key="nag"
                @click="toggleNag(nag)"
                :title="title"
                class="nag-btn"
                :class="{ active: hasNag(nag) }"
              >
                {{ symbol }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Comment Section -->
      <div class="comment-section">
        <h4>Comment</h4>
        <textarea
          v-model="commentText"
          @input="updateComment"
          placeholder="Add a comment for this move..."
          class="comment-input"
        ></textarea>
      </div>

      <!-- Clear Button -->
      <div v-if="hasNags || hasComment" class="action-buttons">
        <button @click="clearAnnotations" class="btn-clear">Clear All</button>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>💡 Select a move to add annotations and comments.</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GameNotes',
  props: {
    currentTreeNode: { type: Object, default: null }
  },
  emits: ['update-node-nags', 'update-node-comment'],
  data() {
    return {
      selectedNags: new Set(),
      commentText: '',
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
        [138, '⇄', 'White has counterplay'],
        [32, '⟳', 'Repetition'],
        [36, '↑', 'Initiative'],
        [40, '→', 'Attack']
      ]
    };
  },
  watch: {
    currentTreeNode: {
      handler(newNode) {
        if (newNode) {
          this.selectedNags = new Set(newNode.nags || []);
          this.commentText = newNode.comment || '';
        }
      },
      immediate: true,
      deep: true
    }
  },
  computed: {
    moveLabel() {
      if (!this.currentTreeNode?.san) return 'Move';
      const moveNum = this.currentTreeNode.move_number || '';
      const color = this.currentTreeNode.color;
      const san = this.currentTreeNode.san;

      if (color === 'w') {
        return `${moveNum}. ${san}`;
      }
      return `${moveNum}... ${san}`;
    },
    hasNags() {
      return this.selectedNags.size > 0;
    },
    hasComment() {
      return this.commentText && this.commentText.trim().length > 0;
    }
  },
  methods: {
    hasNag(nag) {
      return this.selectedNags.has(nag);
    },
    toggleNag(nag) {
      if (this.selectedNags.has(nag)) {
        this.selectedNags.delete(nag);
      } else {
        this.selectedNags.add(nag);
      }
      this.emitUpdates();
    },
    updateComment() {
      this.emitUpdates();
    },
    emitUpdates() {
      this.$emit('update-node-nags', {
        nodeId: this.currentTreeNode.id,
        nags: Array.from(this.selectedNags)
      });
      this.$emit('update-node-comment', {
        nodeId: this.currentTreeNode.id,
        comment: this.commentText
      });
    },
    clearAnnotations() {
      this.selectedNags.clear();
      this.commentText = '';
      this.emitUpdates();
    }
  }
};
</script>

<style scoped>
.game-notes {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 12px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #999;
  font-size: 0.9rem;
}

.empty-state p {
  margin: 0;
  text-align: center;
}

.notes-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.selected-move-header {
  padding: 8px;
  background-color: #f0f7ff;
  border-left: 3px solid #2196F3;
  border-radius: 4px;
}

.selected-move-header h3 {
  margin: 0 0 4px 0;
  font-size: 1.1rem;
  color: #1976D2;
  font-weight: 600;
}

.move-fen {
  margin: 0;
  font-size: 0.8rem;
  color: #999;
}

.nag-section h4,
.comment-section h4 {
  margin: 0 0 8px 0;
  font-size: 0.9rem;
  color: #2c3e50;
  font-weight: 600;
}

.palette-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nag-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.group-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nag-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(42px, 1fr));
  gap: 4px;
}

.nag-btn {
  padding: 6px 3px;
  font-weight: 600;
  font-size: 0.9rem;
  background-color: #f5f5f5;
  border: 1px solid #d0d0d0;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #2c3e50;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
}

.nag-btn:hover {
  background-color: #e8f4f8;
  border-color: #2196F3;
  color: #1976D2;
}

.nag-btn.active {
  background-color: #2196F3;
  color: white;
  border-color: #1976D2;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.4);
}

.comment-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.comment-input {
  padding: 8px;
  font-size: 0.9rem;
  border: 1px solid #d0d0d0;
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
  min-height: 80px;
  max-height: 200px;
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

.action-buttons {
  display: flex;
  justify-content: flex-start;
  gap: 8px;
  margin-top: 8px;
}

.btn-clear {
  padding: 8px 16px;
  font-size: 0.85rem;
  background-color: #f5f5f5;
  color: #d32f2f;
  border: 1px solid #d32f2f;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-clear:hover {
  background-color: #ffebee;
  color: #c62828;
}
</style>

