<template>
  <div class="board-display">
    <button @click="$emit('flip-board')" class="flip-btn">Flip Board</button>
    <div id="svg-container" v-html="svgBoard"></div>
  </div>
</template>

<script>
export default {
  name: 'BoardDisplay',
  props: {
    svgBoard: { type: String, required: true }
  }
};
</script>

<style scoped>
.board-display {
  margin-top: 10px;
  display: inline-block;
}

/* Fixed board area to avoid layout shifts when analysis grows */
#svg-container {
  width: 400px; /* adjust if your board SVG is larger */
  height: 400px;
  overflow: hidden;
}

/* Reuse the original flip button styling from Analyzer.vue */
.flip-btn {
  background-color: #2196F3;
  color: white;
  padding: 6px 12px;
  margin: 5px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
</style>
