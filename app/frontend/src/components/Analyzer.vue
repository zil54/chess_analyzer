<template>
  <div class="analyzer">
    <div class="layout">
      <div class="top-left">
        <PgnPanel
          :pgnData="pgnData"
          :currentMove="currentMove"
          :currentPosition="currentPosition"
          @upload-pgn="uploadPGN"
          :canGoPrev="canGoPrev"
          :canGoNext="canGoNext"
          @go-first="firstMove"
          @go-prev="prevMove"
          @go-next="nextMove"
          @go-last="lastMove"
          @select-move="selectMove"
        />
      </div>

      <div class="mid-left board-area">
        <FenControls
          :fen="fen"
          :isFenValid="isFenValid"
          :canAnalyze="canAnalyze"
          :isAnalyzing="!!socket"
          @update:fen="fen = $event"
          @render-board="renderBoard"
          @start-analysis="analyzeLive"
          @stop-analysis="stopLiveAnalysis"
          @upload-pgn="uploadPGN"
          @flip-board="flipBoard"
        />

        <BoardDisplay
          :svgBoard="svgBoard"
        />

        <LiveAnalysisPanel
          :lines="currentAnalysisLines"
          :statusText="analysisStatusText"
          :isAnalyzingFurther="analysisFurtherActive"
          :activityText="analysisFurtherText"
        />
      </div>

      <aside class="right-panel">
        <PgnMovesList
          :pgnData="pgnData"
          :currentMove="currentMove"
          :currentNodeId="currentTreeNodeId"
          @select-move="selectMove"
          @select-tree-node="selectTreeNode"
        />
      </aside>
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
import PgnMovesList from './PgnMovesList.vue';
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
    PgnMovesList,
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
      currentTreeNodeId: 0,
      // each entry: { depthLabel: string, lines: [{ label: string, text: string }] }
      currentAnalysisLines: [],
      currentAnalysisDepth: 1,
      analysisStatusText: "",
      analysisFurtherActive: false,
      analysisFurtherText: "",
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
    window.addEventListener('keydown', this.handleKeyDown);
  },

  beforeUnmount() {
    this.stopLiveAnalysis();
    window.removeEventListener('keydown', this.handleKeyDown);
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
      if (this.currentTreeNode?.fen) {
        return this.currentTreeNode;
      }
      return this.pgnData.positions[this.currentMove];
    },
    currentTreeNode() {
      if (!this.pgnData?.variation_tree) return null;
      return this.treeNodeMap[this.currentTreeNodeId] || this.pgnData.variation_tree;
    },
    treeNodeMap() {
      const root = this.pgnData?.variation_tree;
      if (!root) return {};

      const map = {};
      const stack = [root];
      while (stack.length) {
        const node = stack.pop();
        if (!node || typeof node !== 'object') continue;
        if (Number.isInteger(node.id)) {
          map[node.id] = node;
        }

        const variations = Array.isArray(node.variations) ? node.variations : [];
        for (let index = variations.length - 1; index >= 0; index -= 1) {
          stack.push(variations[index]);
        }
      }

      return map;
    },
    treeParentMap() {
      const root = this.pgnData?.variation_tree;
      if (!root) return {};

      const map = { 0: null };
      const stack = [root];
      while (stack.length) {
        const node = stack.pop();
        if (!node || typeof node !== 'object') continue;

        const variations = Array.isArray(node.variations) ? node.variations : [];
        for (let index = variations.length - 1; index >= 0; index -= 1) {
          const child = variations[index];
          if (!child || !Number.isInteger(child.id)) continue;
          map[child.id] = Number.isInteger(node.id) ? node.id : null;
          stack.push(child);
        }
      }

      return map;
    },
    canGoPrev() {
      if (!this.pgnData) return false;
      if (this.pgnData?.variation_tree) {
        return this.currentTreeNodeId !== 0 && Number.isInteger(this.treeParentMap[this.currentTreeNodeId]);
      }
      return this.currentMove > 0;
    },
    canGoNext() {
      if (!this.pgnData) return false;
      if (this.pgnData?.variation_tree) {
        return Boolean(this.getContinuationChild(this.currentTreeNode));
      }
      return this.currentMove < this.pgnData.total_moves;
    }
  },

  methods: {
    getContinuationChild(node) {
      const variations = Array.isArray(node?.variations) ? node.variations : [];
      return variations.find((variation) => variation?.is_mainline) || variations[0] || null;
    },

    async showTreeNode(nodeId, preferredMoveIndex = null) {
      if (!this.pgnData?.variation_tree) return;

      const node = this.treeNodeMap[nodeId] || this.pgnData.variation_tree;
      if (!node?.fen) return;

      const wasAnalyzing = !!this.socket;
      this.resetAnalysisState();

      this.currentTreeNodeId = nodeId;
      if (Number.isInteger(preferredMoveIndex)) {
        this.currentMove = preferredMoveIndex;
      } else if (Number.isInteger(node.mainline_index)) {
        this.currentMove = node.mainline_index;
      } else if (Number.isInteger(node.anchor_mainline_index)) {
        this.currentMove = node.anchor_mainline_index;
      }

      this.fen = node.fen;
      await this.renderBoard();

      if (wasAnalyzing) {
        this.sendAnalysisRequest();
      }
    },

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
      this.analysisFurtherActive = false;
      this.analysisFurtherText = "";
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

      if (!displayDepth && !workerDepth) {
        return payload?.message || sourceLabel;
      }

      const displayText = displayDepth > displayTarget
        ? `showing depth ${displayDepth}`
        : `showing depth ${displayDepth}/${displayTarget}`;
      const workerText = `worker ${workerDepth}/${workerTarget}`;
      const progressText = `${displayText} · ${workerText}`;
      if (payload?.type === "status" && payload?.message) {
        return `${payload.message} · ${progressText}`;
      }

      return `${sourceLabel} · ${progressText}`;
    },

    syncAnalysisActivity(payload) {
      const cachedDepth = Number(payload?.cached_depth ?? payload?.display_lock_depth ?? 0) || 0;
      const workerDepth = Number(payload?.worker_depth ?? payload?.depth ?? 0) || 0;
      const unlockDepth = Number(payload?.display_unlock_depth ?? 0) || 0;
      const workerRunning = Boolean(payload?.worker_running);
      const displayLocked = Boolean(payload?.display_locked);
      const isAnalyzingFurther = cachedDepth > 0 && workerRunning && displayLocked;

      this.analysisFurtherActive = isAnalyzingFurther;
      if (!isAnalyzingFurther) {
        this.analysisFurtherText = "";
        return;
      }

      const waitingText = unlockDepth > workerDepth
        ? ` Waiting for worker depth ${unlockDepth}.`
        : "";
      this.analysisFurtherText = `App is analyzing further.${waitingText}`;
    },

    statusLabel(status) {
      const labels = {
        analysis_started: "Live analysis",
        analysis_running: "Live analysis",
        complete: "Analysis complete",
        idle: "Analysis idle",
      };
      return labels[String(status || "")] || "Analysis";
    },

    analyzeLive() {
      if (!this.isFenValid) {
        this.resetAnalysisState("Enter a valid FEN before starting analysis");
        return;
      }

      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.resetAnalysisState("Switching analysis...");
        this.sendAnalysisRequest();
        return;
      }

      this.resetAnalysisState("Connecting to analysis service...");
      if (this.socket) this.socket.close();

      const socketUrl = this.wsUrl("/ws/analyze");
      this.socket = new WebSocket(socketUrl);

      this.socket.onopen = () => {
        this.analysisStatusText = "Live analysis started";
        this.sendAnalysisRequest();
      };
      this.socket.onmessage = (event) => {
        this.handleAnalysisMessage(event.data);
      };
      this.socket.onerror = (err) => {
        this.analysisStatusText = "Analysis connection error";
        this.analysisFurtherActive = false;
        this.analysisFurtherText = "";
        console.error("WS Error", err);
      };
      this.socket.onclose = (event) => {
        this.analysisFurtherActive = false;
        this.analysisFurtherText = "";
        if (!event.wasClean && !this.currentAnalysisLines.length) {
          this.analysisStatusText = "Analysis connection closed before data arrived";
        }
        this.socket = null;
      };
    },

    sendAnalysisRequest() {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
        console.warn("Cannot send analysis request: socket not open");
        return;
      }

      this.socket.send(JSON.stringify({
        fen: this.fen,
        depth: 1, // Start with shallow depth for UI responsiveness
        display_target_depth: 1,
        worker_target_depth: LIVE_ANALYSIS_WORKER_TARGET_DEPTH,
        display_lag_depth: 2, // Lag display behind worker by 2 depths for stability
      }));
      this.analysisStatusText = 'Live analysis updated';
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
              positions: created.positions,
              movetext: created.movetext || null,
              variation_tree: created.variation_tree || null,
              mainline_node_ids: Array.isArray(created.mainline_node_ids) ? created.mainline_node_ids : null,
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
              positions: movesPayload.positions,
              movetext: movesPayload.movetext || created.movetext || null,
              variation_tree: movesPayload.variation_tree || created.variation_tree || null,
              mainline_node_ids: Array.isArray(movesPayload.mainline_node_ids)
                ? movesPayload.mainline_node_ids
                : (Array.isArray(created.mainline_node_ids) ? created.mainline_node_ids : null),
            };
          } else {
            throw new Error("Upload succeeded but no positions were returned.");
          }

          this.pgnData = pgnData;
          this.currentMove = 0;
          this.currentTreeNodeId = 0;
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

      if (this.pgnData?.variation_tree) {
        await this.showTreeNode(this.getMainlineNodeId(moveIndex), moveIndex);
        return;
      }

      const wasAnalyzing = !!this.socket;
      this.resetAnalysisState();

      this.currentTreeNodeId = this.getMainlineNodeId(moveIndex);
      const position = this.pgnData.positions[moveIndex];
      this.fen = position.fen;
      await this.renderBoard();

      if (wasAnalyzing) {
        this.sendAnalysisRequest();
      }
    },

    async selectMove(moveIndex) {
      this.currentMove = moveIndex;
      await this.showPosition(moveIndex);
    },

    getMainlineNodeId(moveIndex) {
      const nodeIds = this.pgnData?.mainline_node_ids;
      if (Array.isArray(nodeIds) && Number.isInteger(nodeIds[moveIndex])) {
        return nodeIds[moveIndex];
      }
      return 0;
    },

    async selectTreeNode(nodeId) {
      await this.showTreeNode(nodeId);
    },

    async nextMove() {
      if (!this.pgnData) return;

      if (this.pgnData?.variation_tree) {
        const nextNode = this.getContinuationChild(this.currentTreeNode);
        if (nextNode?.id != null) {
          await this.showTreeNode(nextNode.id);
        }
        return;
      }

      if (this.currentMove < this.pgnData.total_moves) {
        this.currentMove++;
        await this.showPosition(this.currentMove);
      }
    },

    async prevMove() {
      if (!this.pgnData) return;

      if (this.pgnData?.variation_tree) {
        const parentNodeId = this.treeParentMap[this.currentTreeNodeId];
        if (Number.isInteger(parentNodeId)) {
          await this.showTreeNode(parentNodeId);
        }
        return;
      }

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

    handleKeyDown(event) {
      if (!this.pgnData || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) {
        return;
      }

      const target = event.target;
      if (target instanceof HTMLElement) {
        const tagName = target.tagName;
        if (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(tagName)) {
          return;
        }
      }

      if (event.key === 'ArrowLeft' && this.canGoPrev) {
        event.preventDefault();
        this.prevMove();
      } else if (event.key === 'ArrowRight' && this.canGoNext) {
        event.preventDefault();
        this.nextMove();
      } else if (event.key === 'ArrowUp' && this.canGoPrev) {
        event.preventDefault();
        this.prevMove();
      } else if (event.key === 'ArrowDown' && this.canGoNext) {
        event.preventDefault();
        this.nextMove();
      } else if (event.key === 'Home' && this.currentMove !== 0) {
        event.preventDefault();
        this.firstMove();
      } else if (event.key === 'End' && this.currentMove !== this.pgnData.total_moves) {
        event.preventDefault();
        this.lastMove();
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
        this.analysisFurtherActive = false;
        this.analysisFurtherText = "";
        this.analysisStatusText = payload.message || "Analysis failed";
        console.error("Analysis error:", payload.message || payload);
        return;
      }

      if (payload.type === "status") {
        this.syncAnalysisActivity(payload);
        this.analysisStatusText = this.formatAnalysisStatus(payload, this.statusLabel(payload.status));
        return;
      }

      if (payload.type === "snapshot") {
        this.syncAnalysisActivity(payload);
        const sourceLabel = payload.source === "database" ? "DB" : "Engine";
        this.analysisStatusText = this.formatAnalysisStatus(payload, sourceLabel);
        this.renderSnapshot(payload);
      }
    },

    formatEvaluationValue(scoreCp, scoreMate) {
      if (scoreMate !== null && scoreMate !== undefined && scoreMate !== "") {
        return `#${Number(scoreMate)}`;
      }
      if (scoreCp !== null && scoreCp !== undefined && scoreCp !== "") {
        return (Number(scoreCp) / 100).toFixed(2);
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
            const rawScore = parseInt(scoreMatch[2], 10);

            const evalValue =
              scoreMatch[1] === "cp"
                ? (rawScore / 100).toFixed(2)
                : `#${rawScore}`;

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
  max-width: 1320px;
  width: 100%;
}

input, button {
  margin: 5px;
  padding: 6px 12px;
  font-size: 14px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(460px, 560px) minmax(370px, 485px);
  grid-template-rows: auto auto;
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

.board-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.right-panel {
  grid-column: 2;
  grid-row: 1 / span 2;
  min-width: 0;
}

@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
  }
  .top-left,
  .mid-left,
  .right-panel {
    grid-column: 1;
  }
  .top-left { grid-row: 1; }
  .mid-left { grid-row: 2; }
  .right-panel { grid-row: 3; }
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

