<template>
  <div class="board-display">
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
  width: 100%;
  display: flex;
  justify-content: center;
}

#svg-container {
  width: min(100%, 440px);
  aspect-ratio: 1 / 1;
  overflow: hidden;
}

#svg-container :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
