<template>
  <div v-if="hasContent" class="moves-list">
    <div class="moves-list-title">Game moves</div>
    <div class="moves-section-label">Full PGN (with variations)</div>

    <div v-if="hasVariationTree" class="tree-block">
      <PgnMoveTreeNode
        :node="variationTree"
        :currentNodeId="currentNodeId"
        :renderSelf="false"
        @select-node="$emit('select-tree-node', $event)"
      />
    </div>

    <div v-else class="movetext-block">{{ movetext }}</div>
  </div>
</template>

<script>
import PgnMoveTreeNode from './PgnMoveTreeNode.vue';

export default {
  name: 'PgnMovesList',
  components: {
    PgnMoveTreeNode,
  },
  props: {
    pgnData: { type: Object, default: null },
    currentMove: { type: Number, required: true },
    currentNodeId: { type: Number, default: 0 },
  },
  emits: ['select-move', 'select-tree-node'],
  computed: {
    movetext() {
      const text = this.pgnData?.movetext;
      return typeof text === 'string' ? text.trim() : '';
    },
    variationTree() {
      const tree = this.pgnData?.variation_tree;
      return tree && typeof tree === 'object' ? tree : null;
    },
    hasContent() {
      return this.hasVariationTree || Boolean(this.movetext);
    },
    hasVariationTree() {
      return Array.isArray(this.variationTree?.variations) && this.variationTree.variations.length > 0;
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
  text-align: left;
  width: 100%;
  box-sizing: border-box;
}

.moves-list-title {
  margin-bottom: 6px;
  font-weight: 600;
  color: #2c3e50;
  font-size: 0.9rem;
}

.moves-section-label {
  font-size: 12px;
  font-weight: 600;
  color: #57606a;
  margin-bottom: 6px;
}

.tree-block,
.movetext-block {
  padding: 10px 12px;
  max-height: 420px;
  overflow-y: auto;
  overflow-x: visible;
  background: #fff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 15px;
  line-height: 1.6;
  color: #1f2328;
}

.movetext-block {
  white-space: pre-wrap;
  word-break: break-word;
}

.variation-paren {
  color: #6e7781;
  font-weight: 600;
}
</style>

