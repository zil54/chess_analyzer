<template>
  <span class="move-sequence">
    <span v-if="node.starting_comment" class="move-comment move-comment-start">
      { {{ node.starting_comment }} }
    </span>

    <button
      v-if="node.san"
      type="button"
      class="move-token"
      :class="{ active: currentNodeId === node.id, mainline: node.is_mainline }"
      @click="$emit('select-node', node.id)"
    >
      {{ formattedLabel }}
    </button>

    <span v-if="node.comment" class="move-comment">
      { {{ node.comment }} }
    </span>

    <template v-for="variation in sideVariations" :key="`variation-${variation.id}`">
      <span class="variation-block">
        <span class="variation-paren">(</span>
        <PgnMoveTreeNode
          :node="variation"
          :currentNodeId="currentNodeId"
          :isBranchStart="true"
          @select-node="$emit('select-node', $event)"
        />
        <span class="variation-paren">)</span>
      </span>
    </template>

    <span v-if="mainlineChild" class="continuation">
      <PgnMoveTreeNode
        :node="mainlineChild"
        :currentNodeId="currentNodeId"
        :isBranchStart="false"
        @select-node="$emit('select-node', $event)"
      />
    </span>
  </span>
</template>

<script>
export default {
  name: 'PgnMoveTreeNode',
  props: {
    node: { type: Object, required: true },
    currentNodeId: { type: Number, default: 0 },
    isBranchStart: { type: Boolean, default: false },
  },
  emits: ['select-node'],
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
};
</script>

<style scoped>
.move-sequence {
  display: inline;
  line-height: 1.9;
}

.move-token,
.move-comment,
.variation-block {
  margin-right: 6px;
}

.move-token {
  display: inline-block;
  padding: 1px 4px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #1f2328;
  cursor: pointer;
  font-size: 13px;
  line-height: 1.4;
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

.move-token.active {
  background: #dbeafe;
  color: #1d4ed8;
}

.move-comment {
  color: #57606a;
  font-size: 12px;
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
}

.continuation {
  display: inline;
}
</style>

