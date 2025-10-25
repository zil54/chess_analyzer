<template>
  <div class="analyzer">
    <h2>Enter FEN:</h2>
    <input v-model="fen" />
    <button @click="renderBoard">Render</button>
    <button @click="analyzeStatic">Analyze (Static)</button>
    <button @click="analyzeLive">Analyze (Live)</button>
    <button @click="stopLiveAnalysis">Stop</button>

    <div id="svg-container" v-html="svgBoard"></div>

    <pre class="static-output" v-if="staticOutput">{{ staticOutput }}</pre>
    <div class="live-output">
  <pre v-for="(line, idx) in pvLines" :key="idx">{{ line }}</pre>
</div>


  </div>
</template>

<script>
export default {
  name: 'Analyzer',
data() {
  return {
    fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    svgBoard: "",
    staticOutput: "",
    pvLines: [],
    socket: null
  };
},
  mounted() {
    // ✅ Set the page title when this component is mounted
    document.title = "Chess Analyzer";
  },


  methods: {
    async renderBoard() {
      const res = await fetch("http://localhost:8000/svg", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fen: this.fen })
      });
      this.svgBoard = await res.text();
    },
    async analyzeStatic() {
      this.staticOutput = "";
      const res = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fen: this.fen })
      });
      const data = await res.json();
      if (data.error) {
        this.staticOutput = "Error: " + data.error;
      } else {
        this.staticOutput = data.variations
          .map((v, i) => {
            const score = v.score >= 10000
              ? `Mate in ${v.score - 10000}`
              : `${(v.score / 100).toFixed(2)} eval`;
            return `#${i + 1}: ${v.line.join(" ")} (${score})`;
          })
          .join("\n");
      }
    },
    analyzeLive() {
      this.liveOutput = "";
      if (this.socket) this.socket.close();
      this.socket = new WebSocket("ws://localhost:8000/ws/analyze");

      this.socket.onopen = () => {
        this.socket.send(this.fen);
      };
     this.socket.onmessage = (event) => {
  const line = event.data;
  if (line.includes(" pv ")) {
    this.pvLines.push(line);
  }
};


    this.socket.onerror = (err) => {
  this.pvLines.push("WebSocket error: " + err.message);
};
this.socket.onclose = () => {
  this.pvLines.push("[Analysis stopped]");
};
    },
    stopLiveAnalysis() {
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
    }
  }
};
</script>

<style scoped>
.analyzer {
  text-align: center;
  max-width: 600px;
}
input, button {
  margin: 5px;
  padding: 6px 12px;
  font-size: 14px;
}
#svg-container {
  margin-top: 10px;
}
.static-output {
  color: #2c3e50;
  background-color: #e8f0ff;
  padding: 1rem;
  margin-top: 1rem;
  white-space: pre-wrap;
  border-left: 4px solid #2c3e50;
}
.live-output {
  background-color: #f4f4f4;
  color: #2c3e50;
  padding: 1rem;
  margin-top: 1rem;
  white-space: pre-wrap;
  border-left: 4px solid #4CAF50;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  overflow-x: auto;
  max-width: 93vw;       /* ✅ stretches wider but not full screen */
  text-align: left;      /* ✅ aligns content to the left */
  margin-left: auto;
  margin-right: auto;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}
</style>