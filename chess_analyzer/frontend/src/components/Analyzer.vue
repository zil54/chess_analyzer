<template>
  <div class="analyzer">
    <h2>Enter FEN:</h2>
    <input v-model="fen" />
    <button @click="renderBoard">Render</button>
    <button @click="analyzeLive" :disabled="!canAnalyze || !isFenValid">Analyze (Live)</button>
    <button @click="stopLiveAnalysis">Stop</button>
    <h1>PGN Upload Test</h1>
    <button @click="uploadPGN">Upload PGN</button>

    <div id="svg-container" v-html="svgBoard"></div>

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
      fen: "",
      svgBoard: "",
      pvLines: [],
      socket: null,
    };
  },

  mounted() {
    document.title = "Chess Analyzer";
  },

  computed: {
    canAnalyze() {
      return this.fen && this.fen.trim().length > 0;
    },
    isFenValid() {
      if (!this.fen) return false;
      const parts = this.fen.trim().split(/\s+/);
      return parts.length === 6;
    }
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

    analyzeLive() {
      this.pvLines = [];
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
    },

    async uploadPGN() {
      const fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.accept = ".pgn";
      fileInput.onchange = async () => {
        const file = fileInput.files[0];
        const text = await file.text();

        const createRes = await fetch("http://localhost:8000/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pgn: text })
        });
        const session = await createRes.json();
        const sessionId = session.id;

        const formData = new FormData();
        formData.append("file", file);

        const uploadRes = await fetch(`http://localhost:8000/sessions/${sessionId}/upload_pgn`, {
          method: "POST",
          body: formData
        });
        const data = await uploadRes.json();
        console.log("Stored critical positions:", data.stored);
      };
      fileInput.click();
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
  max-width: 100vw;
  text-align: left;
  margin-left: auto;
  margin-right: auto;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}
</style>