<template>
  <div class="analyzer">
    <div class="layout">
      <div class="top-left">
        <PgnPanel
          :pgnData="pgnData"
          :currentMove="currentMove"
          :currentPosition="currentPosition"
          @upload-pgn="uploadPGN"
          @go-first="firstMove"
          @go-prev="prevMove"
          @go-next="nextMove"
          @go-last="lastMove"
        />
      </div>

      <div class="mid-left">
        <BoardDisplay
          :svgBoard="svgBoard"
          @flip-board="flipBoard"
        />
      </div>

      <aside class="mid-right">
        <LiveAnalysisPanel :lines="currentAnalysisLines" :statusText="analysisStatusText" />
      </aside>

      <div class="bottom-left">
        <FenControls
          :fen="fen"
          :isFenValid="isFenValid"
          :canAnalyze="canAnalyze"
          :isAnalyzing="!!socket"
          @update:fen="fen = $event"
          @render-board="renderBoard"
          @start-analysis="analyzeLive"
          @stop-analysis="stopLiveAnalysis"
        />
      </div>

      <!-- bottom-right intentionally empty for now -->
      <div class="bottom-right" />
    </div>
  </div>
</template>

<script>
import { Chess } from 'chess.js';
import {
  LIVE_ANALYSIS_DISPLAY_LAG_DEPTH,
  LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH,
  LIVE_ANALYSIS_WORKER_TARGET_DEPTH,
} from '../config/liveAnalysis';
import FenControls from './FenControls.vue';
import PgnPanel from './PgnPanel.vue';
import BoardDisplay from './BoardDisplay.vue';
import LiveAnalysisPanel from './LiveAnalysisPanel.vue';

const DEFAULT_BACKEND_PORT = '8000';

function normalizeBaseUrl(url) {
  return String(url || '').trim().replace(/\/+$/, '');
}

function getApiBaseUrl() {
  const configured = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL);
  if (configured) return configured;

  if (typeof window === 'undefined') {
    return `http://127.0.0.1:${DEFAULT_BACKEND_PORT}`;
  }

  const { origin, protocol, hostname, port } = window.location;
  if (port === '5173' || port === '4173') {
    return `${protocol}//${hostname}:${DEFAULT_BACKEND_PORT}`;
  }

  return normalizeBaseUrl(origin);
}

function buildApiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalizedPath}`;
}

function buildWebSocketUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return buildApiUrl(normalizedPath).replace(/^http/i, 'ws');
}

export default {
  name: 'Analyzer',
  components: {
    FenControls,
    PgnPanel,
    BoardDisplay,
    LiveAnalysisPanel
  },
  data() {
    return {
      fen: "",
      svgBoard: "",
      pvLines: [],
      socket: null,
      pgnData: null,
      currentMove: 0,
      // each entry: { depthLabel: string, lines: [{ label: string, text: string }] }
      currentAnalysisLines: [],
      currentAnalysisDepth: 1,
      analysisStatusText: "",
      boardFlipped: false,
      waitingForDepthOne: false,

      // UI smoothing: keep a depth block steady for a short time before updating
      analysisHoldMs: 1200,
      pendingAnalysisLines: null,
      pendingDepth: null,
      pendingTimer: null,
      lastRenderedAt: 0,

      gameId: null,
    };
  },

  mounted() {
    document.title = "Chess Analyzer";
    // Set default starting position
    this.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    this.renderBoard();
  },

  beforeUnmount() {
    this.stopLiveAnalysis();
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

    resetAnalysisState(statusText = "") {
      this.pvLines = [];
      this.currentAnalysisLines = [];
      this.currentAnalysisDepth = 0;
      this.analysisStatusText = statusText;
      this.waitingForDepthOne = false;
      this.lastRenderedAt = 0;

      if (this.pendingTimer) {
        clearTimeout(this.pendingTimer);
        this.pendingTimer = null;
      }

      this.pendingAnalysisLines = null;
      this.pendingDepth = null;
    },

    apiUrl(path) {
      return buildApiUrl(path);
    },

    wsUrl(path) {
      return buildWebSocketUrl(path);
    },

    async renderBoard() {
      const res = await fetch(this.apiUrl("/svg"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fen: this.fen, flip: this.boardFlipped })
      });
      this.svgBoard = await res.text();
    },

    formatAnalysisStatus(payload, sourceLabel = "Analysis") {
      const displayDepth = Number(payload?.depth ?? payload?.display_depth ?? 0) || 0;
      const displayTarget = Number(payload?.display_target_depth ?? payload?.target_depth ?? LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH) || LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH;
      const workerDepth = Number(payload?.worker_depth ?? displayDepth) || displayDepth;
      const workerTarget = Number(payload?.worker_target_depth ?? displayTarget) || displayTarget;

      if (payload?.type === "status" && payload?.message) {
        return payload.message;
      }

      if (!displayDepth && !workerDepth) {
        return sourceLabel;
      }

      return `${sourceLabel}: showing depth ${displayDepth}/${displayTarget} · worker ${workerDepth}/${workerTarget}`;
    },

    analyzeLive() {
      if (!this.isFenValid) {
        this.resetAnalysisState("Enter a valid FEN before starting analysis");
        return;
      }

      this.resetAnalysisState("Connecting to analysis service...");
      if (this.socket) this.socket.close();

      const socketUrl = this.wsUrl("/ws/analyze");
      this.socket = new WebSocket(socketUrl);

      this.socket.onopen = () => {
        this.analysisStatusText = "Live analysis started";
        this.socket.send(JSON.stringify({
          fen: this.fen,
          depth: LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH,
          display_target_depth: LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH,
          worker_target_depth: LIVE_ANALYSIS_WORKER_TARGET_DEPTH,
          display_lag_depth: LIVE_ANALYSIS_DISPLAY_LAG_DEPTH,
        }));
      };
      this.socket.onmessage = (event) => {
        this.handleAnalysisMessage(event.data);
      };
      this.socket.onerror = (err) => {
        this.analysisStatusText = "Analysis connection error";
        console.error("WS Error", err);
      };
      this.socket.onclose = (event) => {
        if (!event.wasClean && !this.currentAnalysisLines.length) {
          this.analysisStatusText = "Analysis connection closed before data arrived";
        }
        this.socket = null;
      };
    },

    stopLiveAnalysis() {
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
      this.resetAnalysisState("Analysis stopped");
    },

    stringifyError(error, fallback = "Unknown error") {
      if (!error) return fallback;
      if (typeof error === "string") return error;
      if (error instanceof Error) return error.message || fallback;
      if (Array.isArray(error)) {
        const parts = error
          .map((item) => this.stringifyError(item, ""))
          .filter(Boolean);
        return parts.length ? parts.join("; ") : fallback;
      }
      if (typeof error === "object") {
        if (typeof error.detail === "string") return error.detail;
        if (error.detail) return this.stringifyError(error.detail, fallback);
        if (typeof error.message === "string") return error.message;
        try {
          return JSON.stringify(error);
        } catch (_) {
          return fallback;
        }
      }
      return String(error);
    },

    async readErrorResponse(response, fallback) {
      try {
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          const payload = await response.json();
          return this.stringifyError(payload, fallback);
        }

        const text = await response.text();
        return text || fallback;
      } catch (error) {
        console.error("Error reading response payload:", error);
        return fallback;
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
          console.log(`Uploading PGN to: ${this.apiUrl("/games")}`);

          const createRes = await fetch(this.apiUrl("/games"), {
            method: "POST",
            body: formData
          });

          console.log("POST /games response status:", createRes.status);

          if (!createRes.ok) {
            const errorMsg = await this.readErrorResponse(createRes, "Failed to upload PGN");
            console.error("Upload error:", errorMsg);
            alert(`Error: ${errorMsg}`);
            return;
          }

          const created = await createRes.json();
          console.log("POST /games payload:", created);

          let pgnData;
          this.gameId = created.id ?? null;

          if (Array.isArray(created.positions)) {
            pgnData = {
              success: true,
              headers: created.headers,
              total_moves: created.total_moves,
              positions: created.positions
            };
          } else if (this.gameId != null) {
            const movesRes = await fetch(this.apiUrl(`/games/${this.gameId}/moves`));
            console.log("GET /games/{id}/moves response status:", movesRes.status);

            if (!movesRes.ok) {
              const errorMsg = await this.readErrorResponse(movesRes, "Failed to load moves");
              console.error("Load moves error:", errorMsg);
              alert(`Error: ${errorMsg}`);
              return;
            }

            const movesPayload = await movesRes.json();
            console.log("Loaded positions:", movesPayload.total_moves);

            pgnData = {
              success: true,
              headers: created.headers,
              total_moves: movesPayload.total_moves,
              positions: movesPayload.positions
            };
          } else {
            throw new Error("Upload succeeded but no positions were returned.");
          }

          this.pgnData = pgnData;
          this.currentMove = 0;
          await this.showPosition(0);
          console.log("PGN upload successful");

          if (this.gameId != null) {
            console.log("Starting batch analysis of all positions...");
            try {
              const analyzeRes = await fetch(this.apiUrl(`/games/${this.gameId}/analyze`), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  depth: 15,
                  time_limit: 1.0
                })
              });

              if (analyzeRes.ok) {
                const analyzeResult = await analyzeRes.json();
                console.log("✓ Batch analysis complete:", analyzeResult);
              } else {
                const errorMsg = await this.readErrorResponse(analyzeRes, "Batch analysis skipped");
                console.warn("Batch analysis skipped:", errorMsg);
              }
            } catch (analyzeErr) {
              console.warn("Batch analysis not available:", this.stringifyError(analyzeErr, "Unknown error"));
            }
          }
        } catch (error) {
          const errorMsg = this.stringifyError(error, "Failed to upload PGN");
          console.error("Upload exception:", error);
          alert(`Error: ${errorMsg}`);
        }
      };
      fileInput.click();
    },

    async showPosition(moveIndex) {
      if (!this.pgnData || moveIndex < 0 || moveIndex > this.pgnData.total_moves) return;

      // Stop any ongoing analysis
      this.stopLiveAnalysis();
      // Clear previous analysis
      this.resetAnalysisState();

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

    handleAnalysisMessage(message) {
      if (!message) return;

      let payload = null;
      try {
        payload = JSON.parse(message);
      } catch (_) {
        payload = null;
      }

      if (!payload) {
        if (typeof message === "string" && message.includes(" pv ")) {
          this.pvLines.push(message);
          this.updateAnalysisDisplay();
        }
        return;
      }

      if (payload.type === "error") {
        this.analysisStatusText = payload.message || "Analysis failed";
        console.error("Analysis error:", payload.message || payload);
        return;
      }

      if (payload.type === "status") {
        this.analysisStatusText = this.formatAnalysisStatus(payload, String(payload.status || "analysis").replaceAll("_", " "));
        return;
      }

      if (payload.type === "snapshot") {
        const sourceLabel = payload.source === "database" ? "DB" : "Engine";
        this.analysisStatusText = this.formatAnalysisStatus(payload, sourceLabel);
        this.renderSnapshot(payload);
      }
    },

    formatEvaluationValue(scoreCp, scoreMate) {
      const fenParts = (this.fen || "").trim().split(/\s+/);
      const sideToMove = fenParts.length >= 2 ? fenParts[1] : 'w';
      const sign = sideToMove === 'b' ? -1 : 1;

      if (scoreMate !== null && scoreMate !== undefined && scoreMate !== "") {
        return `#${Number(scoreMate) * sign}`;
      }
      if (scoreCp !== null && scoreCp !== undefined && scoreCp !== "") {
        return (Number(scoreCp) * sign / 100).toFixed(2);
      }
      return "--";
    },

    renderSnapshot(snapshot) {
      const depth = parseInt(snapshot.depth || 0, 10);
      const lines = Array.isArray(snapshot.lines) ? snapshot.lines : [];
      if (!depth || lines.length === 0) return;

      const depthLines = lines.map((line, idx) => {
        const pvUci = line.pv || "";
        const pvAlgebraic = pvUci ? this.convertToAlgebraic(pvUci, this.fen) : "";
        const evalValue = this.formatEvaluationValue(line.score_cp, line.score_mate);
        return {
          label: `Line ${line.line_number || idx + 1}:`,
          text: `${evalValue} ${pvAlgebraic}`.trim()
        };
      });

      this.applyAnalysisDisplay(
        [
          {
            depthLabel: `[Depth ${depth}]`,
            lines: depthLines
          }
        ],
        depth
      );
    },

    applyAnalysisDisplay(newDisplay, latestDepth) {
      if (latestDepth === this.currentAnalysisDepth) {
        this.currentAnalysisLines = newDisplay;
        this.lastRenderedAt = Date.now();
        return;
      }

      const now = Date.now();
      const elapsed = now - (this.lastRenderedAt || 0);
      const remainingHold = Math.max(0, this.analysisHoldMs - elapsed);

      this.pendingAnalysisLines = newDisplay;
      this.pendingDepth = latestDepth;

      if (this.pendingTimer) {
        clearTimeout(this.pendingTimer);
        this.pendingTimer = null;
      }

      if (remainingHold === 0) {
        this.currentAnalysisLines = this.pendingAnalysisLines;
        this.currentAnalysisDepth = this.pendingDepth;
        this.pendingAnalysisLines = null;
        this.pendingDepth = null;
        this.lastRenderedAt = Date.now();
      } else {
        this.pendingTimer = setTimeout(() => {
          this.currentAnalysisLines = this.pendingAnalysisLines || this.currentAnalysisLines;
          if (this.pendingDepth != null) {
            this.currentAnalysisDepth = this.pendingDepth;
          }
          this.pendingAnalysisLines = null;
          this.pendingDepth = null;
          this.pendingTimer = null;
          this.lastRenderedAt = Date.now();
        }, remainingHold);
      }
    },

    updateAnalysisDisplay() {
      if (this.pvLines.length === 0) return;

      const linesByDepth = {};
      // Display all depths (1+), but database only stores depth >= 15

      for (const line of this.pvLines) {
        const depthMatch = line.match(/depth (\d+)/);
        const scoreMatch = line.match(/score (cp|mate) (-?\d+)/);
        const pvMatch = line.match(/pv (.+)$/);

        if (depthMatch && scoreMatch) {
          const depth = parseInt(depthMatch[1]);

          if (!linesByDepth[depth]) {
            linesByDepth[depth] = [];
          }
          if (linesByDepth[depth].length < 3) {  // Keep all 3 lines
            const fenParts = (this.fen || "").trim().split(/\s+/);
            const sideToMove = fenParts.length >= 2 ? fenParts[1] : 'w';
            const sign = sideToMove === 'b' ? -1 : 1;

            const rawScore = parseInt(scoreMatch[2], 10);
            const normalizedScore = rawScore * sign;

            const evalValue =
              scoreMatch[1] === "cp"
                ? (normalizedScore / 100).toFixed(2)
                : `#${normalizedScore}`;

            const pvUci = pvMatch ? pvMatch[1] : "";
            const pvAlgebraic = pvUci
              ? this.convertToAlgebraic(pvUci, this.fen)
              : "";

            linesByDepth[depth].push({ eval: evalValue, pv: pvAlgebraic });
          }
        }
      }

      const depths = Object.keys(linesByDepth)
        .map((d) => parseInt(d))
        .sort((a, b) => a - b);

      if (depths.length === 0) return;

      const latestDepth = depths[depths.length - 1];
      const latestLines = linesByDepth[latestDepth];
      const depthLines = latestLines.map((line, idx) => ({
        label: `Line ${idx + 1}:`,
        text: `${line.eval} ${line.pv}`
      }));

      this.applyAnalysisDisplay(
        [
          {
            depthLabel: `[Depth ${latestDepth}]`,
            lines: depthLines
          }
        ],
        latestDepth
      );
    }
  }
};
</script>

<style scoped>
.analyzer {
  text-align: center;
  max-width: 1200px;
  width: 100%;
}

input, button {
  margin: 5px;
  padding: 6px 12px;
  font-size: 14px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(420px, 520px) minmax(320px, 420px);
  grid-template-rows: auto auto auto;
  gap: 16px;
  align-items: start;
  justify-content: center;
  padding: 0 12px;
}

.top-left {
  grid-column: 1;
  grid-row: 1;
  min-width: 0;
}

.mid-left {
  grid-column: 1;
  grid-row: 2;
  min-width: 0;
}

.mid-right {
  grid-column: 2;
  grid-row: 2;
  min-width: 0;
}

.bottom-left {
  grid-column: 1;
  grid-row: 3;
  min-width: 0;
}

.bottom-right {
  grid-column: 2;
  grid-row: 3;
}

@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto auto;
  }
  .top-left,
  .mid-left,
  .mid-right,
  .bottom-left,
  .bottom-right {
    grid-column: 1;
  }
  .top-left { grid-row: 1; }
  .mid-left { grid-row: 2; }
  .mid-right { grid-row: 3; }
  .bottom-left { grid-row: 4; }
  .bottom-right { display: none; }
}

/* Live analysis card styling (kept here because LiveAnalysisPanel only defines inner scroll styles) */
.live-output {
  background-color: #f4f4f4;
  color: #2c3e50;
  padding: 1rem;
  margin-top: 0; /* in grid row with board; avoid extra vertical offset */
  border-left: 4px solid #4CAF50;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  overflow-x: hidden;
  word-wrap: break-word;
  overflow-wrap: break-word;
  text-align: left;
  max-width: 100%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border-radius: 4px;
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
  color: #2c3e50;
  font-weight: bold;
  min-width: 100px;
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
</style>

