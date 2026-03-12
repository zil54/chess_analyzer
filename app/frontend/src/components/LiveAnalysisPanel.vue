<template>
  <div class="live-output" v-if="hasContent">
    <div class="analysis-status" v-if="statusText">{{ statusText }}</div>
    <div class="live-output-scroll" v-if="lines && lines.length > 0">
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
  </div>
</template>

<script>
export default {
  name: 'LiveAnalysisPanel',
  props: {
    lines: { type: Array, required: true },
    statusText: { type: String, default: '' }
  },
  computed: {
    hasContent() {
      return (this.lines && this.lines.length > 0) || !!this.statusText;
    }
  }
};
</script>

<style scoped>
.live-output-scroll {
  /* Keep the surrounding card the same size and make the content scroll as it grows */
  max-height: 35vh;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
}

.analysis-status {
  margin-bottom: 10px;
  font-weight: 600;
  color: #2c3e50;
}

.pv-line-label {
  font-weight: bold;
}
.pv-line-row {
  /* ensure each line appears on its own row */
  display: block;
}
</style>
