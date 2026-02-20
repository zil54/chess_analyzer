<template>
  <div class="app">
    <Analyzer />
  </div>
</template>

<script>
import Analyzer from './components/Analyzer.vue';

export default {
  name: 'App',
  components: {
    Analyzer
  }
};
</script>

<style>
body {
  margin: 0;
  font-family: Arial, sans-serif;
  background-color: #f0f0f0;
}
.app {
  display: grid;
  place-items: center;
  min-height: 100vh;
}
</style>