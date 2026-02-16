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

    <button @click="flipBoard" class="flip-btn">Flip Board</button>

    <div id="svg-container" v-html="svgBoard"></div>

    <!-- Updated analysis output -->
    <div class="live-output" v-if="currentAnalysisLines.length > 0">
      <div v-for="(lineData, idx) in currentAnalysisLines" :key="idx" class="analysis-line">
        <span class="eval-value">{{ lineData.eval }}</span>
        <span class="pv-moves">{{ lineData.pv }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { Chess } from 'chess.js';

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
      currentAnalysisLines: [],
      currentAnalysisDepth: 1,
      boardFlipped: false,
      waitingForDepthOne: false,
    };
  },

  mounted() {
    document.title = "Chess Analyzer";
    // Set default starting position
    this.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    this.renderBoard();
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
    convertToAlgebraic(uciMoves, fenString) {
      /**
       * Convert a string of UCI moves to algebraic notation with correct move numbers
       * @param {string} uciMoves - Space-separated UCI moves (e.g., "e2e4 e7e5")
       * @param {string} fenString - Starting FEN position
       * @returns {string} Algebraic notation with move numbers
       */
      try {
        const game = new Chess(fenString);
        const moves = uciMoves.trim().split(/\s+/);
        const result = [];

        // Extract the move number from FEN (6th field)
        const fenParts = fenString.split(' ');
        const fullmoveNumber = parseInt(fenParts[5]) || 1;

        // Determine if it's White's turn (FEN field 2)
        const isWhiteTurn = fenParts[1] === 'w';

        // Calculate current move number
        let currentMoveNum = fullmoveNumber;
        let isWhiteMove = isWhiteTurn;

        // Only use ellipsis for Black's first move if we're in the middle of a game
        // (i.e., not at the starting position where fullmoveNumber === 1)
        const useEllipsis = !isWhiteTurn && fullmoveNumber > 1;

        for (const uciMove of moves) {
          // Try to convert UCI move to algebraic
          const moveObj = game.moves({ verbose: true }).find(
            m => m.from + m.to === uciMove || (m.promotion && m.from + m.to + m.promotion === uciMove)
          );

          if (moveObj) {
            if (isWhiteMove) {
              // White's move: "1. e4"
              result.push(`${currentMoveNum}.`);
            } else {
              // Black's move
              if (result.length === 0 && useEllipsis) {
                // First move is Black's and we're not at game start: use ellipsis "4...c5"
                result.push(`${currentMoveNum}...`);
              } else {
                // Not the first move or we're at game start: just add the move number once before Black's first move
                if (result.length === 0) {
                  result.push(`${currentMoveNum}.`);
                }
              }
            }

            // Make the move
            const move = game.move(uciMove);
            if (move) {
              result.push(move.san);
            }

            // Update move tracking
            if (!isWhiteMove) {
              // After Black's move, increment the move number for next White move
              currentMoveNum++;
            }
            isWhiteMove = !isWhiteMove;
          }
        }

        return result.join(' ');
      } catch (error) {
        // Fallback to UCI notation if conversion fails
        return uciMoves;
      }
    },

    async renderBoard() {
      const res = await fetch("http://localhost:8000/svg", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fen: this.fen, flip: this.boardFlipped })
      });
      this.svgBoard = await res.text();
    },

    analyzeLive() {
      // reset UI buffers
      this.pvLines = [];
      this.currentAnalysisLines = [];
      this.currentAnalysisDepth = 1;
      this.waitingForDepthOne = true;
      if (this.socket) this.socket.close();
      this.socket = new WebSocket("ws://localhost:8000/ws/analyze");

      this.socket.onopen = () => {
        console.log("WS Open, sending fen:", this.fen);
        this.socket.send(this.fen);
      };
      this.socket.onmessage = (event) => {
        const line = event.data;
        // console.log("WS Recv:", line);
        if (!line || !line.includes(" pv ")) return;
        const depthMatch = line.match(/depth (\d+)/);

        if (this.waitingForDepthOne) {
          if (!depthMatch) return;
          const d = parseInt(depthMatch[1]);
          // If the depth matches our expectations of a new search (low depth), start collecting.
          // Otherwise, if it's unreasonably high immediately (e.g. > 20), it might be stale buffer.
          // But 5 was too restrictive if engine is fast. Let's try 10 or just accept any depth if we are sure backend resets.
          // Since backend does "stop" and "ucinewgame", we should trust the new output.
          // Let's just reset on the first depth we see effectively.

          this.pvLines = [];
          this.currentAnalysisLines = [];
          this.currentAnalysisDepth = d;
          this.waitingForDepthOne = false;
        }

        this.pvLines.push(line);
        this.updateAnalysisDisplay();
      };
      this.socket.onerror = (err) => {
        console.error("WS Error", err);
        this.pvLines.push("WebSocket error");
      };
      this.socket.onclose = () => {
        console.log("WS Closed");
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

      // Stop any ongoing analysis
      this.stopLiveAnalysis();
      // Clear previous analysis
      this.pvLines = [];
      this.currentAnalysisLines = [];
      this.currentAnalysisDepth = 0;

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
    },

    flipBoard() {
      this.boardFlipped = !this.boardFlipped;
      if (this.fen) {
        this.renderBoard();
      }
    },

    updateAnalysisDisplay() {
      if (this.pvLines.length === 0) return;

      const linesByDepth = {};

      for (const line of this.pvLines) {
        const depthMatch = line.match(/depth (\d+)/);
        const scoreMatch = line.match(/score (cp|mate) (-?\d+)/);
        const pvMatch = line.match(/pv (.+)$/);

        if (depthMatch && scoreMatch) {
          const depth = parseInt(depthMatch[1]);
          if (!linesByDepth[depth]) {
            linesByDepth[depth] = [];
          }
          if (linesByDepth[depth].length < 3) {
            let evalValue = scoreMatch[1] === 'cp' ? (parseInt(scoreMatch[2], 10) / 100).toFixed(2) : `#${scoreMatch[2]}`;
            const pvUci = pvMatch ? pvMatch[1] : '';
            const pvAlgebraic = pvUci ? this.convertToAlgebraic(pvUci, this.fen) : '';
            linesByDepth[depth].push({ eval: evalValue, pv: pvAlgebraic });
          }
        }
      }

      const depths = Object.keys(linesByDepth).map(d => parseInt(d)).sort((a, b) => a - b);

      // Display ONLY the current (latest) depth to avoid old depths lingering
      if (depths.length === 0) return;

      const currentDepth = depths[depths.length - 1];
      this.currentAnalysisDepth = currentDepth;

      const linesForDepth = linesByDepth[currentDepth];
      const formattedLines = linesForDepth.map((line, idx) =>
        `Line ${idx + 1}: ${line.eval} ${line.pv}`
      ).join('\n\n');

      this.currentAnalysisLines = [{ eval: `Depth ${currentDepth}:`, pv: formattedLines }];
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
  border-left: 4px solid #4CAF50;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  overflow-x: hidden;
  word-wrap: break-word;
  overflow-wrap: break-word;
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
.analysis-row {
  margin: 8px 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  padding: 8px;
  background-color: #fafafa;
  border-radius: 4px;
}
.depth-label {
  font-weight: bold;
  margin-bottom: 5px;
  color: #2c3e50;
}
.analysis-header {
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 10px;
  font-size: 14px;
}
.analysis-line {
  display: flex;
  align-items: flex-start;
  gap: 15px;
  width: 100%;
  margin-bottom: 4px;
  flex-wrap: nowrap;
}
.eval-value {
  background-color: #e1f5fe;
  padding: 4px 12px;
  border-radius: 3px;
  font-family: 'Courier New', Courier, monospace;
  color: #01579b;
  font-weight: bold;
  min-width: 70px;
  text-align: right;
  flex-shrink: 0;
}
.pv-moves {
  font-family: 'Courier New', Courier, monospace;
  color: #555;
  font-size: 12px;
  flex: 1;
  word-wrap: break-word;
  overflow-wrap: break-word;
  word-break: break-word;
  white-space: pre-wrap;
}
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