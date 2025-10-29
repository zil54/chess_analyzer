<template>
  <div class="analyzer">
    <h2>Enter FEN:</h2>
    <input v-model="fen" />
    <button @click="renderBoard">Render</button>
    <button @click="analyzeLive" :disabled="!canAnalyze || !isFenValid">Analyze (Live)</button>
    <button @click="stopLiveAnalysis">Stop</button>
    <h1>PGN Upload</h1>
    <button @click="uploadPGN">Upload PGN File</button>

    <div v-if="pgnData" class="pgn-info">
      <h3>{{ pgnData.headers.white }} vs {{ pgnData.headers.black }}</h3>
      <p>{{ pgnData.headers.event }} - {{ pgnData.headers.date }}</p>
      <p>Result: {{ pgnData.headers.result }}</p>
      <div class="move-controls">
        <button @click="firstMove" :disabled="currentMove === 0">⏮ First</button>
        <button @click="prevMove" :disabled="currentMove === 0">◀ Prev</button>
        <span>Move {{ currentMove }} / {{ pgnData.total_moves }}</span>
        <button @click="nextMove" :disabled="currentMove === pgnData.total_moves">Next ▶</button>
        <button @click="lastMove" :disabled="currentMove === pgnData.total_moves">Last ⏭</button>
      </div>
      <div v-if="currentPosition" class="current-move">
        <strong v-if="currentPosition.san">{{ currentPosition.san }}</strong>
        <span v-else>Starting position</span>
      </div>
    </div>

    <div id="svg-container" v-html="svgBoard"></div>

    <div class="live-output" v-if="pvLines.length > 0">
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
      pgnData: null,
      currentMove: 0,
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
    },
    currentPosition() {
      if (!this.pgnData) return null;
      return this.pgnData.positions[this.currentMove];
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
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);

        try {
          const response = await fetch("http://localhost:8000/analyze_pgn", {
            method: "POST",
            body: formData
          });

          if (!response.ok) {
            const error = await response.json();
            alert(`Error: ${error.detail}`);
            return;
          }

          this.pgnData = await response.json();
          this.currentMove = 0;
          this.showPosition(0);
        } catch (error) {
          alert(`Failed to upload PGN: ${error.message}`);
        }
      };
      fileInput.click();
    },

    async showPosition(moveIndex) {
      if (!this.pgnData || moveIndex < 0 || moveIndex > this.pgnData.total_moves) return;

      const position = this.pgnData.positions[moveIndex];
      this.fen = position.fen;
      await this.renderBoard();
    },

    async nextMove() {
      if (this.currentMove < this.pgnData.total_moves) {
        this.currentMove++;
        await this.showPosition(this.currentMove);
      }
    },

    async prevMove() {
      if (this.currentMove > 0) {
        this.currentMove--;
        await this.showPosition(this.currentMove);
      }
    },

    async firstMove() {
      this.currentMove = 0;
      await this.showPosition(0);
    },

    async lastMove() {
      this.currentMove = this.pgnData.total_moves;
      await this.showPosition(this.currentMove);
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
.pgn-info {
  margin: 20px 0;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.pgn-info h3 {
  margin: 0 0 10px 0;
  color: #2c3e50;
}
.pgn-info p {
  margin: 5px 0;
  color: #666;
}
.move-controls {
  margin: 15px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}
.move-controls button {
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.move-controls button:hover:not(:disabled) {
  background-color: #45a049;
}
.move-controls button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
.move-controls span {
  font-weight: bold;
  color: #2c3e50;
}
.current-move {
  margin-top: 10px;
  font-size: 18px;
  color: #4CAF50;
}
</style>