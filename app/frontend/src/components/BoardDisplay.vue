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
  width: 100%;
  display: flex;
  justify-content: center;
}

#svg-container {
  width: min(100%, 560px);
  aspect-ratio: 1 / 1;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-radius: 4px;
}

#svg-container :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
