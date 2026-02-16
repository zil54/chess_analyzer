<template>
  <div class="live-output" v-if="lines && lines.length > 0">
    <div
      v-for="(depthBlock, depthIdx) in lines"
      :key="depthIdx"
      class="analysis-line"
    >
      <!-- Depth label in its own chip/column -->
      <span class="eval-value">{{ depthBlock.depthLabel }}</span>

      <!-- PV lines stacked; Line 1 will always start on a new line next to the depth chip -->
      <div class="pv-moves">
        <div
          v-for="(pvLine, lineIdx) in depthBlock.lines"
          :key="lineIdx"
          class="pv-line-row"
        >
          <span class="pv-line-label">{{ pvLine.label }}</span>
          <span class="pv-line-text"> {{ pvLine.text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LiveAnalysisPanel',
  props: {
    lines: { type: Array, required: true }
  }
};
</script>

<style scoped>
.pv-line-label {
  font-weight: bold;
}
.pv-line-row {
  /* ensure each line appears on its own row */
  display: block;
}
</style>
