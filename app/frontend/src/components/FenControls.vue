<template>
  <div class="fen-controls">
    <h2>Enter FEN:</h2>
    <input :value="fen" @input="$emit('update:fen', $event.target.value)" />
    <button @click="$emit('render-board')">Render</button>
    <button
      @click="$emit('start-analysis')"
      :disabled="!canAnalyze || !isFenValid || isAnalyzing"
    >
      Analyze (Live)
    </button>
    <button
      @click="$emit('stop-analysis')"
      :disabled="!isAnalyzing"
    >
      Stop
    </button>
  </div>
</template>

<script>
export default {
  name: 'FenControls',
  props: {
    fen: { type: String, required: true },
    isFenValid: { type: Boolean, required: true },
    canAnalyze: { type: Boolean, required: true },
    isAnalyzing: { type: Boolean, required: true }
  }
};
</script>

<style scoped>
.fen-controls {
  margin-bottom: 10px;
}
</style>

