<template>
  <div v-if="hasContent" class="moves-list">
    <div class="moves-list-title">Game moves</div>
    <div class="moves-section-label">Full PGN (with variations)</div>

    <div v-if="hasVariationTree" class="tree-block">
      <template v-if="rootMainlineNode">
        <PgnMoveTreeNode
          :node="rootMainlineNode"
          :currentNodeId="currentNodeId"
          :isBranchStart="true"
          @select-node="$emit('select-tree-node', $event)"
        />
      </template>

      <template v-for="variation in rootSideVariations" :key="`root-variation-${variation.id}`">
        <span class="root-variation-inline">
          <span class="variation-paren">(</span>
          <PgnMoveTreeNode
            :node="variation"
            :currentNodeId="currentNodeId"
            :isBranchStart="true"
            @select-node="$emit('select-tree-node', $event)"
          />
          <span class="variation-paren">)</span>
        </span>
      </template>
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
    rootVariations() {
      return Array.isArray(this.variationTree?.variations) ? this.variationTree.variations : [];
    },
    rootMainlineNode() {
      return this.rootVariations.find((variation) => variation?.is_mainline) || this.rootVariations[0] || null;
    },
    rootSideVariations() {
      return this.rootVariations.filter((variation) => variation && variation.id !== this.rootMainlineNode?.id);
    },
    hasVariationTree() {
      return this.rootVariations.length > 0;
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
}

.moves-list-title {
  margin-bottom: 8px;
  font-weight: 600;
  color: #2c3e50;
}

.moves-section-label {
  font-size: 13px;
  font-weight: 600;
  color: #57606a;
  margin-bottom: 8px;
}

.tree-block,
.movetext-block {
  padding: 10px;
  max-height: 340px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #1f2328;
}

.movetext-block {
  white-space: pre-wrap;
  word-break: break-word;
}

.root-variation-inline {
  display: inline;
  margin-left: 6px;
}

.variation-paren {
  color: #6e7781;
  font-weight: 600;
}
</style>

