<template>
  <div class="analyzer">
    <div v-if="isUploading" class="upload-overlay">
      <div class="upload-spinner"></div>
      <p>{{ uploadStatus }}</p>
    </div>
    <div class="layout">
      <!-- LEFT SECTION: Vertically stacked options -->
      <aside class="left-sidebar">
        <FenControls
          :fen="fen"
          :isFenValid="isFenValid"
          :canAnalyze="canAnalyze"
          :isAnalyzing="!!socket"
          @update:fen="fen = $event"
          @render-board="renderBoard"
          @start-analysis="analyzeLive"
          @stop-analysis="stopLiveAnalysis"
          @upload-pgn="triggerUpload"
          @flip-board="flipBoard"
        />
        <input type="file" ref="fileInput" @change="uploadPGN" accept=".pgn" style="display: none" />
      </aside>

      <!-- CENTER SECTION: Board, navigation arrows, analysis -->
      <div class="center-stage board-area">
        <BoardDisplay
          :fen="fen"
          :flipped="boardFlipped"
          @user-move="onUserMove"
        />

        <div class="board-controls" v-if="pgnData">
          <button @click="firstMove" :disabled="currentMove === 0">|&lt; First</button>
          <button @click="prevMove" :disabled="!canGoPrev">&lt; Prev</button>
          <button @click="nextMove" :disabled="!canGoNext">Next &gt;</button>
          <button @click="lastMove" :disabled="currentMove === pgnData.total_moves">Last &gt;|</button>
        </div>

        <LiveAnalysisPanel
          :lines="currentAnalysisLines"
          :statusText="analysisStatusText"
          :isAnalyzingFurther="analysisFurtherActive"
          :activityText="analysisFurtherText"
        />
      </div>

      <!-- RIGHT SECTION: Tabs -->
      <aside class="right-panel">
        <div class="tabs-header">
          <button :class="{active: activeTab === 'PGN'}" @click="activeTab = 'PGN'">
            PGN<span v-if="hasUnsavedChanges"> *</span>
          </button>
          <button
            :class="{active: activeTab === 'Games'}"
            @click="activeTab = 'Games'"
            :disabled="sessionGames.length === 0"
          >
            Games ({{sessionGames.length}})
          </button>
          <button :class="{active: activeTab === 'Quiz'}" @click="activeTab = 'Quiz'" disabled>Quiz</button>
        </div>

        <div class="tab-content" v-show="activeTab === 'PGN'">
          <div v-if="!pgnData" class="empty-state">
            <p>Upload a PGN file or choose a game to see its moves here.</p>
          </div>
          <template v-else>
            <PgnPanel
              :pgnData="pgnData"
              :currentMove="currentMove"
              :currentPosition="currentPosition"
            />
            <PgnMovesList
              :pgnData="pgnData"
              :currentMove="currentMove"
              :currentNodeId="currentTreeNodeId"
              @select-move="selectMove"
              @select-tree-node="selectTreeNode"
            />
            <div v-if="hasUnsavedChanges" class="pgn-save-actions">
              <button @click="saveChanges" class="btn-save">Save</button>
              <button @click="discardChanges" class="btn-discard">Cancel</button>
            </div>
          </template>
        </div>

        <div class="tab-content" v-show="activeTab === 'Games' && sessionGames.length > 0">
          <GameSelector
            :games="sessionGames"
            :initialGameId="gameId"
            @select-game="loadGame"
          />
        </div>

        <div class="tab-content" v-show="activeTab === 'Quiz'">
          <p>Quiz mode coming soon...</p>
        </div>
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
import GameSelector from './GameSelector.vue';

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
    LiveAnalysisPanel,
    GameSelector
    },
  data() {
    return {
      activeTab: 'PGN',
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
      games: [],
      sessionGameIds: [],
      isUploading: false,
      uploadStatus: "",

      hasUnsavedChanges: false,
      unsavedNodeIds: [],
      backupTreeNodeId: null,
    };
  },

  mounted() {
    document.title = "Chess Analyzer";
    // Set default starting position
    this.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    this.renderBoard();
    this.fetchGames();
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
    sessionGames() {
      return this.games.filter(g => this.sessionGameIds.includes(g.id));
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
    async fetchGames() {
      try {
        const response = await fetch(buildApiUrl('/games'));
        const data = await response.json();
        if (data.success) {
          this.games = data.games;
        }
      } catch (err) {
        console.error("Failed to fetch games:", err);
      }
    },

    async loadGame(gameId) {
      try {
        const wasAnalyzing = !!this.socket;
        if (this.socket) {
          this.socket.close();
          this.socket = null;
        }
        this.resetAnalysisState("");

        this.uploadStatus = "Loading game moves...";
        this.isUploading = true;

        const response = await fetch(buildApiUrl(`/games/${gameId}/moves`));
        const data = await response.json();
        if (data.success) {
          this.gameId = data.game_id;
          this.pgnData = {
            headers: data.headers || {},
            total_moves: data.total_moves,
            positions: data.positions,
            movetext: data.movetext,
            variation_tree: data.variation_tree,
            mainline_node_ids: data.mainline_node_ids
          };
          this.currentMove = 0;
          this.currentTreeNodeId = 0;
          this.fen = this.pgnData.positions[0].fen;
          await this.renderBoard();

          if (wasAnalyzing) {
            this.analyzeLive();
          }
        }
      } catch (err) {
        console.error("Failed to load game:", err);
      } finally {
        this.isUploading = false;
        this.uploadStatus = "";
      }
    },

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

      // Attempt to resolve mainline index if present to keep board controls aligned
      if (Number.isInteger(preferredMoveIndex)) {
        this.currentMove = preferredMoveIndex;
      } else if (Number.isInteger(node.mainline_index)) {
        this.currentMove = node.mainline_index;
      } else if (Number.isInteger(node.anchor_mainline_index)) {
        this.currentMove = node.anchor_mainline_index;
      } else if (Number.isInteger(node.ply)) {
        this.currentMove = node.ply;
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
      // Replaced by vue3-chessboard rendering automatically
    },

    generateNewNodeId() {
      let maxId = 0;
      const root = this.pgnData?.variation_tree;
      if (!root) return 1;

      const stack = [root];
      while (stack.length) {
        const node = stack.pop();
        if (node && Number.isInteger(node.id) && node.id > maxId) {
          maxId = node.id;
        }
        const vars = Array.isArray(node.variations) ? node.variations : [];
        for (let i = 0; i < vars.length; i++) {
          stack.push(vars[i]);
        }
      }
      return maxId + 1;
    },

    async onUserMove(moveInfo) {
      if (!this.pgnData || !this.pgnData.variation_tree) {
        this.fen = moveInfo.fen;
        if (this.socket) this.analyzeLive();
        return;
      }

      const parentNode = this.currentTreeNode || this.pgnData.variation_tree;
      const parentNodeId = Number.isInteger(parentNode.id) ? parentNode.id : 0;

      // Extract algebraic notation
      let san = moveInfo.san;
      if (!san) {
        try {
          const chess = new Chess(parentNode.fen);
          const moveResult = chess.move({
            from: moveInfo.from,
            to: moveInfo.to,
            promotion: moveInfo.promotion || 'q'
          });
          if (moveResult) san = moveResult.san;
        } catch (err) {
          console.warn("Invalid user move recalculation", err);
          san = null;
        }
      }

      if (!san) return;

      const newPly = (parentNode.ply || 0) + 1;
      const newColor = newPly % 2 === 1 ? 'w' : 'b';
      const newMoveNumber = Math.ceil(newPly / 2);

      const newId = this.generateNewNodeId();
      const newNode = {
        id: newId,
        san: san,
        fen: moveInfo.fen,
        ply: newPly,
        color: newColor,
        move_number: newMoveNumber,
        is_mainline: false,
        variations: []
      };

      if (!parentNode.variations) parentNode.variations = [];
      parentNode.variations.push(newNode);

      if (!this.hasUnsavedChanges) {
        this.hasUnsavedChanges = true;
        this.backupTreeNodeId = parentNodeId;
        this.unsavedNodeIds = [];
      }
      this.unsavedNodeIds.push(newId);

      // Force Vue to recognize deep reactivity by replacing array
      parentNode.variations = [...parentNode.variations];

      await this.selectTreeNode(newId);
    },

    saveChanges() {
      // Logic for saving custom variations to the backend can go here.
      // For now, commit them locally.
      this.hasUnsavedChanges = false;
      this.unsavedNodeIds = [];
      this.backupTreeNodeId = null;
    },

    discardChanges() {
      if (!this.pgnData?.variation_tree) return;

      const prune = (node) => {
        if (!node || !Array.isArray(node.variations)) return;
        node.variations = node.variations.filter(v => !this.unsavedNodeIds.includes(v.id));
        node.variations.forEach(prune);
      };

      prune(this.pgnData.variation_tree);

      if (this.backupTreeNodeId !== null) {
        this.showTreeNode(this.backupTreeNodeId);
      }

      this.hasUnsavedChanges = false;
      this.unsavedNodeIds = [];
      this.backupTreeNodeId = null;
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

    triggerUpload() {
      this.$refs.fileInput.click();
    },

    async uploadPGN(event) {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);

      this.isUploading = true;
      this.uploadStatus = `Uploading and processing ${file.name}...`;

      try {
        const response = await fetch(buildApiUrl('/games'), {
          method: 'POST',
          body: formData,
        });
        const data = await response.json();
        if (data.success) {
          const totalProcessed = data.total_games_created || 1;
          this.uploadStatus = `Successfully processed ${totalProcessed} games!`;
          // Brief pause to show success status before loading
          await new Promise(r => setTimeout(r, 1000));

          // Track session games - all_created_ids from response
          const createdIds = data.all_created_ids || [data.id];
          this.sessionGameIds = createdIds;

          // Refresh games list and select the new game
          await this.fetchGames();
          this.loadGame(data.id);
        }
      } catch (err) {
        console.error("Upload failed", err);
        this.uploadStatus = "Upload failed: " + (err.message || String(err));
        // Keep status visible for a few seconds if it's an error
        await new Promise(r => setTimeout(r, 3000));
      } finally {
        this.isUploading = false;
        this.uploadStatus = "";
      }
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
  position: relative;
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
  grid-template-columns: 60px minmax(460px, 560px) minmax(370px, 485px);
  gap: 16px;
  align-items: start;
  justify-content: center;
  padding: 0 12px;
}

.left-sidebar {
  grid-column: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 10px;
}

.center-stage {
  grid-column: 2;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.right-panel {
  grid-column: 3;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tabs-header {
  display: flex;
  border-bottom: 2px solid #e0e0e0;
}

.tabs-header button {
  background: none;
  border: none;
  padding: 8px 16px;
  margin: 0;
  cursor: pointer;
  font-weight: bold;
  color: #666;
}

.tabs-header button.active {
  color: #2196F3;
  border-bottom: 2px solid #2196F3;
  margin-bottom: -2px;
}

.tabs-header button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-state {
  padding: 30px 15px;
  color: #888;
  font-style: italic;
  background: #fafafa;
  border-radius: 8px;
  border: 1px dashed #ddd;
  margin-top: 10px;
}

.board-controls {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 5px;
}

@media (max-width: 1080px) {
  .layout {
    grid-template-columns: 60px 1fr;
    grid-template-rows: auto auto;
  }
  .left-sidebar { grid-column: 1; grid-row: 1; }
  .center-stage { grid-column: 2; grid-row: 1; }
  .right-panel { grid-column: 1 / span 2; grid-row: 2; }
}

@media (max-width: 600px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .left-sidebar { grid-column: 1; flex-direction: row; justify-content: center; }
  .center-stage { grid-column: 1; }
  .right-panel { grid-column: 1; }
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

.upload-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.upload-spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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
  max-height: 400px;
  overflow-y: auto;
}

.pgn-save-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
  justify-content: center;
}

.pgn-save-actions button {
  padding: 8px 16px;
  font-weight: bold;
}

.btn-save {
  background-color: #4CAF50;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
}
.btn-discard {
  background-color: #95a5a6;
  color: white;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.btn-discard:hover {
  background-color: #7f8c8d;
}

/* ...existing code... */
</style>

