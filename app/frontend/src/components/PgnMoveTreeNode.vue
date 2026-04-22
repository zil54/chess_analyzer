<template>
  <span class="move-sequence">
    <span v-if="renderSelf && node.starting_comment" class="move-comment move-comment-start">
      { {{ node.starting_comment }} }
    </span>

    <span v-if="renderSelf && node.san" class="move-item">
      <button
        type="button"
        class="move-token"
        :class="{ active: currentNodeId === node.id, mainline: node.is_mainline }"
        @click="selectMove"
      >
        {{ formattedLabel }}
        <span v-if="nagDisplay" class="move-nag">{{ nagDisplay }}</span>
      </button>
    </span>


    <span v-if="renderSelf && node.comment" class="move-comment">
      { {{ node.comment }} }
    </span>

    <template v-if="renderContinuation && mainlineChild">
      <span class="continuation">
        <PgnMoveTreeNode
          :node="mainlineChild"
          :currentNodeId="currentNodeId"
          :isBranchStart="false"
          :renderSelf="true"
          :renderContinuation="false"
          @select-node="$emit('select-node', $event)"
          @update-node-nags="$emit('update-node-nags', $event)"
          @update-node-comment="$emit('update-node-comment', $event)"
        />
      </span>

      <template v-for="variation in sideVariations" :key="`variation-${variation.id}`">
        <span class="variation-block">
          <span class="variation-paren">(</span>
          <PgnMoveTreeNode
            :node="variation"
            :currentNodeId="currentNodeId"
            :isBranchStart="true"
            @select-node="$emit('select-node', $event)"
            @update-node-nags="$emit('update-node-nags', $event)"
            @update-node-comment="$emit('update-node-comment', $event)"
          />
          <span class="variation-paren">)</span>
        </span>
      </template>

      <span class="continuation">
        <PgnMoveTreeNode
          :node="mainlineChild"
          :currentNodeId="currentNodeId"
          :isBranchStart="false"
          :renderSelf="false"
          :renderContinuation="true"
          @select-node="$emit('select-node', $event)"
          @update-node-nags="$emit('update-node-nags', $event)"
          @update-node-comment="$emit('update-node-comment', $event)"
        />
      </span>
    </template>
  </span>
</template>

<script>
export default {
  name: 'PgnMoveTreeNode',
  props: {
    node: { type: Object, required: true },
    currentNodeId: { type: Number, default: 0 },
    isBranchStart: { type: Boolean, default: false },
    renderSelf: { type: Boolean, default: true },
    renderContinuation: { type: Boolean, default: true },
  },
  emits: ['select-node'],
  data() {
    return {
      allNags: [
        [1, '!', 'Good move'],
        [2, '?', 'Bad move'],
        [3, '!!', 'Excellent move'],
        [4, '??', 'Blunder'],
        [5, '!?', 'Interesting'],
        [6, '?!', 'Dubious'],
        [10, '=', 'Equal'],
        [14, '+=', 'Slightly better for White'],
        [15, '=+', 'Slightly better for Black'],
        [16, '+/-', 'Better for White'],
        [17, '-/+', 'Better for Black'],
        [18, '+-', 'Winning for White'],
        [19, '-+', 'Winning for Black'],
        [12, '∞', 'Unclear'],
        [130, 'Z', 'Zugzwang'],
        [138, '⇄', 'Counterplay'],
        [32, '⟳', 'Repetition'],
        [36, '↑', 'Initiative'],
        [40, '→', 'Attack'],
        [22, '+/−', 'Advantage/Disadvantage'],
        [23, '−/+', 'Disadvantage/Advantage'],
        [131, '+/=', 'Compensation(W)'],
        [133, '=/+', 'Compensation(B)']
      ]
    };
  },
  watch: {
    node: {
      handler(newNode) {
        // Watchers kept minimal for simple selection
      },
      immediate: true,
      deep: true
    }
  },
  computed: {
    formattedLabel() {
      if (!this.node?.san) {
        return '';
      }

      if (this.node.color === 'w') {
        return `${this.node.move_number}. ${this.node.san}`;
      }

      if (this.isBranchStart) {
        return `${this.node.move_number}... ${this.node.san}`;
      }

      return this.node.san;
    },
    nagDisplay() {
      const display = this.node?.nag_display;
      return typeof display === 'string' && display.trim() ? display.trim() : '';
    },
    variations() {
      return Array.isArray(this.node?.variations) ? this.node.variations : [];
    },
    mainlineChild() {
      return this.variations.find((variation) => variation?.is_mainline) || this.variations[0] || null;
    },
    sideVariations() {
      return this.variations.filter((variation) => variation && variation.id !== this.mainlineChild?.id);
    },
  },
  methods: {
    selectMove() {
      this.$emit('select-node', this.node.id);
    }
  }
};
</script>

<style scoped>
.move-sequence {
  display: inline;
  line-height: 1.6;
}

.move-item {
  display: inline-block;
  margin-right: 2px;
}

.move-token,
.move-comment,
.variation-block {
  margin-right: 0;
}

.move-token {
  display: inline-block;
  padding: 1px 3px;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: #1f2328;
  cursor: pointer;
  font-size: 15px;
  line-height: 1.3;
  font-weight: 400;
}

.move-token:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.move-token.mainline {
  font-weight: 700;
  color: #111827;
}

.move-nag {
  margin-left: 2px;
  color: #6b7280;
  font-weight: 500;
  font-size: 1em;
}

.move-token.active {
  background: #dbeafe;
  color: #1d4ed8;
}

.move-token.active .move-nag {
  color: inherit;
}

.move-comment {
  color: #57606a;
  font-size: 13px;
  margin-left: 2px;
}

.move-comment-start {
  font-style: italic;
}

.variation-block {
  display: inline;
}

.variation-paren {
  color: #6e7781;
  font-weight: 600;
  margin: 0 1px;
}

.continuation {
  display: inline;
}
</style>


