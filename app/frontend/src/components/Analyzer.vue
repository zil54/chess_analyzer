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
          @open-board-settings="toggleBoardSettings"
        />
        <div v-if="isBoardSettingsOpen" class="board-settings-anchor">
          <BoardSettingsPanel
            :boardThemes="boardThemes"
            :selectedBoardThemeId="selectedBoardThemeId"
            @close="isBoardSettingsOpen = false"
            @select-board-theme="applyBoardTheme"
          />
        </div>
        <input type="file" ref="fileInput" @change="uploadPGN" accept=".pgn" style="display: none" />
      </aside>

      <!-- CENTER SECTION: Board, navigation arrows, analysis -->
      <div class="center-stage board-area">
        <BoardDisplay
          ref="boardDisplay"
          :fen="fen"
          :flipped="boardFlipped"
          :boardTheme="selectedBoardTheme"
          :allowFreeEdit="!pgnData"
          @user-move="onUserMove"
        />

        <div class="board-controls">
          <button @click="firstMove" :disabled="currentMove === 0">|&lt; First</button>
          <button @click="prevMove" :disabled="!canGoPrev">&lt; Prev</button>
          <button @click="nextMove" :disabled="!canGoNext">Next &gt;</button>
          <button @click="lastMove" :disabled="!pgnData || currentMove === pgnData.total_moves">Last &gt;|</button>
        </div>
      </div>

      <!-- RIGHT SECTION: Tabs -->
      <aside class="right-panel">
        <div class="tabs-header">
          <button :class="{active: activeTab === 'PGN'}" @click="activeTab = 'PGN'" :disabled="quizModeDisablesOtherTabs">
            PGN<span v-if="hasUnsavedChanges"> *</span>
          </button>
          <button
            :class="{active: activeTab === 'Games'}"
            @click="activeTab = 'Games'"
            :disabled="sessionGames.length === 0 || quizModeDisablesOtherTabs"
          >
            Games ({{sessionGames.length}})
          </button>
          <button :class="{active: activeTab === 'Analysis'}" @click="activeTab = 'Analysis'" :disabled="quizModeDisablesOtherTabs">Analysis</button>
          <button
            :class="{active: activeTab === 'Quiz'}"
            @click="activeTab = 'Quiz'"
            :disabled="!quizPositions.length"
          >
            Quiz
          </button>
        </div>

        <div class="tab-content" v-show="activeTab === 'PGN'">
          <div v-if="!pgnData" class="empty-state">
            <p>Upload a PGN file, choose a game, or start moving on the board to create a new unsaved game.</p>
          </div>
          <template v-else>
            <PgnPanel
              :pgnData="pgnData"
              :currentMove="currentMove"
              :currentPosition="currentPosition"
              :currentTreeNode="currentTreeNode"
              @update-node-nags="updateNodeNags"
              @update-node-comment="updateNodeComment"
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
            <div v-if="pgnData" class="pgn-quiz-action">
              <button
                @click="initiateQuiz"
                class="btn-start-quiz"
                :disabled="quizPositions.length === 0"
              >
                <span v-if="quizPositions.length > 0">
                   Start Critical Position Quiz ({{ quizPositions.length }})
                </span>
                <span v-else>
                  ❌ No Critical Positions (add {CPosition} in comments)
                </span>
              </button>
            </div>
          </template>
        </div>

        <div class="tab-content" v-show="activeTab === 'Games' && sessionGames.length > 0">
          <GameSelector
            :games="sessionGames"
            :initialGameId="gameId"
            :displayedGameId="gameId"
            @select-game="loadGame"
          />
        </div>

        <div class="tab-content" v-show="activeTab === 'Analysis'">
          <LiveAnalysisPanel
            :lines="currentAnalysisLines"
            :statusText="analysisStatusText"
            :isAnalyzingFurther="analysisFurtherActive"
            :activityText="analysisFurtherText"
          />
        </div>

         <div class="tab-content" v-show="activeTab === 'Quiz'">
           <QuizTab
             ref="quizTab"
             :positions="quizPositions"
             :gameId="gameId"
              :startingFen="currentGameStartFen"
             :apiBaseUrl="getApiBaseUrl()"
             @start-quiz="handleStartQuiz"
             @stop-quiz="handleStopQuiz"
             @show-position="handleQuizShowPosition"
             @quiz-finished="handleQuizFinished"
             @quiz-mode-changed="handleQuizModeChanged"
             @quiz-exit-first-move="handleQuizExitFirstMove"
             @flip-board="flipBoard"
           />
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
import {
  BOARD_THEMES,
  DEFAULT_BOARD_THEME_ID,
} from '../config/boardAppearance';
import FenControls from './FenControls.vue';
import BoardSettingsPanel from './BoardSettingsPanel.vue';
import PgnPanel from './PgnPanel.vue';
import PgnMovesList from './PgnMovesList.vue';
import BoardDisplay from './BoardDisplay.vue';
import LiveAnalysisPanel from './LiveAnalysisPanel.vue';
import GameSelector from './GameSelector.vue';
import QuizTab from './QuizTab.vue';

const DEFAULT_BACKEND_PORT = '8000';
const BOARD_APPEARANCE_STORAGE_KEY = 'chess-analyzer-board-appearance';

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

const STANDARD_START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

export default {
  name: 'Analyzer',
  components: {
    FenControls,
    BoardSettingsPanel,
    PgnPanel,
    PgnMovesList,
    BoardDisplay,
    LiveAnalysisPanel,
    GameSelector,
    QuizTab,
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
      boardThemes: BOARD_THEMES,
      selectedBoardThemeId: DEFAULT_BOARD_THEME_ID,
      isBoardSettingsOpen: false,
      waitingForDepthOne: false,

      // UI smoothing: keep a depth block steady for a short time before updating
      analysisHoldMs: 1200,
      analysisRenderMinMs: 500,
      analysisStatusMinMs: 350,
      pendingAnalysisLines: null,
      pendingDepth: null,
      pendingTimer: null,
      lastRenderedAt: 0,
      lastStatusRenderedAt: 0,
      lastStatusText: "",
      analysisPvCache: Object.create(null),

      gameId: null,
      games: [],
      sessionGameIds: [],
      isUploading: false,
      uploadStatus: "",

      hasUnsavedChanges: false,
      unsavedNodeIds: [],
      backupTreeNodeId: null,

       quizPositions: [],
       isQuizActive: false,
       quizModeDisablesOtherTabs: false,
    };
  },

  mounted() {
    document.title = "Chess Analyzer";
    this.restoreBoardAppearance();
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
      return this.fen && this.fen.trim().length > 0 && !this.isQuizActive && !this.quizModeDisablesOtherTabs;
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
      if (this.isQuizActive || this.quizModeDisablesOtherTabs) return false;
      if (!this.pgnData) return false;
      if (this.pgnData?.variation_tree) {
        return this.currentTreeNodeId !== 0 && Number.isInteger(this.treeParentMap[this.currentTreeNodeId]);
      }
      return this.currentMove > 0;
    },
    canGoNext() {
      if (this.isQuizActive || this.quizModeDisablesOtherTabs) return false;
      if (!this.pgnData) return false;
      if (this.pgnData?.variation_tree) {
        return Boolean(this.getContinuationChild(this.currentTreeNode));
      }
      return this.currentMove < this.pgnData.total_moves;
    },
    selectedBoardTheme() {
      return this.boardThemes.find((theme) => theme.id === this.selectedBoardThemeId) || this.boardThemes[0];
    },
    currentGameStartFen() {
      return this.pgnData?.positions?.[0]?.fen || STANDARD_START_FEN;
    }
  },

    methods: {
    // Expose the API base URL so child components (QuizTab) can make direct backend calls
    getApiBaseUrl() {
      return getApiBaseUrl();
    },

    getTodayPgnDate() {
      const now = new Date();
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      return `${yyyy}.${mm}.${dd}`;
    },

    createScratchGameFromFen(startFen) {
      const rootFen = typeof startFen === 'string' && startFen.trim() ? startFen.trim() : STANDARD_START_FEN;
      this.gameId = null;
      this.pgnData = {
        headers: {
          event: 'New Analysis Game',
          site: 'Local Analysis Board',
          date: this.getTodayPgnDate(),
          round: '-',
          white: 'Analysis White',
          black: 'Analysis Black',
          result: '*',
        },
        total_moves: 0,
        positions: [{ ply: 0, fen: rootFen, comment: null, cp_tag: false }],
        movetext: '*',
        variation_tree: {
          id: 0,
          ply: 0,
          move_number: 0,
          color: null,
          move: null,
          san: null,
          fen: rootFen,
          comment: null,
          starting_comment: null,
          nags: [],
          nag_symbols: [],
          nag_display: null,
          is_mainline: true,
          mainline_index: 0,
          anchor_mainline_index: 0,
          variations: [],
        },
        mainline_node_ids: [0],
        isScratchGame: true,
      };
      this.currentMove = 0;
      this.currentTreeNodeId = 0;
      this.refreshQuizPositions();
    },

    getMainlineChild(node) {
      const variations = Array.isArray(node?.variations) ? node.variations : [];
      return variations.find((variation) => variation?.is_mainline) || null;
    },

    serializePgnComment(comment) {
      if (!comment) return '';
      const normalized = String(comment).replace(/[{}]/g, '').trim();
      return normalized ? `{${normalized}}` : '';
    },

    serializePgnNags(nags) {
      if (!Array.isArray(nags) || !nags.length) return '';
      return nags
        .filter((nag) => Number.isInteger(nag) || /^\d+$/.test(String(nag)))
        .map((nag) => `$${Number(nag)}`)
        .join(' ');
    },

    serializeMovePrefix(node) {
      if (!node) return '';
      return node.color === 'w' ? `${node.move_number}.` : `${node.move_number}...`;
    },

    serializeVariationBranch(node) {
      if (!node) return '';

      const parts = [this.serializeMovePrefix(node), node.san].filter(Boolean);
      const nags = this.serializePgnNags(node.nags);
      if (nags) parts.push(nags);
      const comment = this.serializePgnComment(node.comment);
      if (comment) parts.push(comment);

      const children = Array.isArray(node.variations) ? node.variations : [];
      const mainlineChild = children.find((child) => child?.is_mainline) || children[0] || null;
      const sideLines = children.filter((child) => child && child !== mainlineChild);
      for (const sideLine of sideLines) {
        const branchText = this.serializeVariationBranch(sideLine);
        if (branchText) parts.push(`(${branchText})`);
      }
      if (mainlineChild) {
        const continuation = this.serializeVariationBranch(mainlineChild);
        if (continuation) parts.push(continuation);
      }

      return parts.join(' ').trim();
    },

    rebuildScratchGameData() {
      if (!this.pgnData?.isScratchGame || !this.pgnData?.variation_tree) return;

      const positions = [{
        ply: 0,
        fen: this.pgnData.variation_tree.fen,
        comment: this.pgnData.variation_tree.comment || null,
        cp_tag: Boolean(this.pgnData.variation_tree.cp_tag),
      }];
      const mainlineNodeIds = [0];
      let node = this.pgnData.variation_tree;
      while (true) {
        const child = this.getMainlineChild(node);
        if (!child) break;
        mainlineNodeIds.push(child.id);
        positions.push({
          ply: child.ply,
          san: child.san,
          fen: child.fen,
          color: child.color,
          move_number: child.move_number,
          comment: child.comment || null,
          cp_tag: Boolean(child.cp_tag),
        });
        node = child;
      }

      this.pgnData.positions = positions;
      this.pgnData.total_moves = Math.max(0, positions.length - 1);
      this.pgnData.mainline_node_ids = mainlineNodeIds;

      const movetextParts = [];
      const rootComment = this.serializePgnComment(this.pgnData.variation_tree.comment);
      if (rootComment) movetextParts.push(rootComment);

      const rootChildren = Array.isArray(this.pgnData.variation_tree.variations) ? this.pgnData.variation_tree.variations : [];
      const mainlineChild = rootChildren.find((child) => child?.is_mainline) || rootChildren[0] || null;
      const sideLines = rootChildren.filter((child) => child && child !== mainlineChild);
      for (const sideLine of sideLines) {
        const branchText = this.serializeVariationBranch(sideLine);
        if (branchText) movetextParts.push(`(${branchText})`);
      }
      if (mainlineChild) {
        const mainlineText = this.serializeVariationBranch(mainlineChild);
        if (mainlineText) movetextParts.push(mainlineText);
      }

      const resultToken = this.pgnData.headers?.result || '*';
      this.pgnData.movetext = [movetextParts.join(' ').trim(), resultToken].filter(Boolean).join(' ').trim();
      this.refreshQuizPositions();
    },

    buildScratchGamePgn() {
      if (!this.pgnData?.variation_tree) return '';
      if (this.pgnData?.isScratchGame) {
        this.rebuildScratchGameData();
      }

      const headers = this.pgnData.headers || {};
      const orderedHeaders = [
        ['Event', headers.event || 'New Analysis Game'],
        ['Site', headers.site || 'Local Analysis Board'],
        ['Date', headers.date || this.getTodayPgnDate()],
        ['Round', headers.round || '-'],
        ['White', headers.white || 'Analysis White'],
        ['Black', headers.black || 'Analysis Black'],
        ['Result', headers.result || '*'],
      ];
      const setupHeaders = [];
      const startFen = this.pgnData.positions?.[0]?.fen || STANDARD_START_FEN;
      if (startFen !== STANDARD_START_FEN) {
        setupHeaders.push(['SetUp', '1']);
        setupHeaders.push(['FEN', startFen]);
      }

      const headerText = [...orderedHeaders, ...setupHeaders]
        .map(([key, value]) => `[${key} "${String(value ?? '').replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"]`)
        .join('\n');

      return `${headerText}\n\n${this.pgnData.movetext || (headers.result || '*')}\n`;
    },

    toggleBoardSettings() {
      this.isBoardSettingsOpen = !this.isBoardSettingsOpen;
    },

    applyBoardTheme(themeId) {
      if (!this.boardThemes.some((theme) => theme.id === themeId)) return;
      this.selectedBoardThemeId = themeId;
      this.persistBoardAppearance();
    },

    restoreBoardAppearance() {
      if (typeof window === 'undefined') return;
      try {
        const raw = window.localStorage.getItem(BOARD_APPEARANCE_STORAGE_KEY);
        if (!raw) return;
        const parsed = JSON.parse(raw);
        if (parsed?.boardThemeId && this.boardThemes.some((theme) => theme.id === parsed.boardThemeId)) {
          this.selectedBoardThemeId = parsed.boardThemeId;
        }
      } catch (error) {
        console.warn('Failed to restore board appearance', error);
      }
    },

    persistBoardAppearance() {
      if (typeof window === 'undefined') return;
      try {
        window.localStorage.setItem(BOARD_APPEARANCE_STORAGE_KEY, JSON.stringify({
          boardThemeId: this.selectedBoardThemeId,
        }));
      } catch (error) {
        console.warn('Failed to persist board appearance', error);
      }
    },

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

          await this.$nextTick();
          this.refreshQuizPositions();
          await this.$nextTick();
          if (this.$refs.quizTab?.markPGNSaved) {
            this.$refs.quizTab.markPGNSaved();
          }

          this.fetchQuizData(gameId);

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

    async fetchQuizData(gameId) {
      const localQuizPositions = this.buildQuizPositionsFromCurrentGame();
      this.quizPositions = localQuizPositions;
      if (!gameId) {
        await this.$nextTick();
        if (this.$refs.quizTab?.markPGNSaved) {
          this.$refs.quizTab.markPGNSaved();
        }
        return;
      }

      try {
        const response = await fetch(buildApiUrl(`/games/${gameId}/quiz`));
        const data = await response.json();
        if (data.success && Array.isArray(data.quiz_positions) && data.quiz_positions.length >= localQuizPositions.length) {
          this.quizPositions = data.quiz_positions || [];
        }
      } catch (err) {
        console.error("Failed to fetch quiz data:", err);
      } finally {
        await this.$nextTick();
        if (this.$refs.quizTab?.markPGNSaved) {
          this.$refs.quizTab.markPGNSaved();
        }
      }
    },

    commentHasCriticalPosition(comment) {
      return typeof comment === 'string' && comment.toLowerCase().includes('cposition');
    },

    commentMarksCurrentMoveAsCritical(comment) {
      if (typeof comment !== 'string') return false;
      const normalized = comment.toLowerCase();
      return normalized.includes('already critical move')
        || normalized.includes('was already critical')
        || normalized.includes('this was already critical');
    },

    normalizeQuizColor(color) {
      return String(color || '').toUpperCase() === 'B' ? 'B' : 'W';
    },

    buildQuizPositionsFromCurrentGame() {
      if (!this.pgnData) {
        return [];
      }

      const positions = Array.isArray(this.pgnData.positions) ? this.pgnData.positions : [];
      if (positions.length === 0) {
        return [];
      }

      if (this.pgnData?.variation_tree && Array.isArray(this.pgnData.mainline_node_ids) && this.pgnData.mainline_node_ids.length > 0) {
        const quizPositions = [];
        // Check starting position (ply = 0) for critical position
        const rootNode = this.pgnData.variation_tree;
        if (rootNode && (Boolean(rootNode.cp_tag) || this.commentHasCriticalPosition(rootNode.comment))) {
          // Starting position is marked critical, quiz should start from first move
          if (this.pgnData.mainline_node_ids.length > 1) {
            const firstNodeId = this.pgnData.mainline_node_ids[1];
            const firstNode = this.treeNodeMap[firstNodeId];
            if (firstNode && positions[0]) {
              quizPositions.push({
                ply: 1,
                fen_before: positions[0].fen,
                expected_move_san: firstNode.san,
                color: this.normalizeQuizColor(firstNode.color),
                comment: rootNode.comment || null,
              });
            }
          }
        }
        // Continue with remaining nodes
        for (let ply = 1; ply < this.pgnData.mainline_node_ids.length; ply += 1) {
          const nodeId = this.pgnData.mainline_node_ids[ply];
          const node = this.treeNodeMap[nodeId];
          if (!node) continue;

          const isCriticalPosition = Boolean(node.cp_tag) || this.commentHasCriticalPosition(node.comment);
          if (!isCriticalPosition) continue;

          const usesCurrentMove = this.commentMarksCurrentMoveAsCritical(node.comment);
          const targetPly = usesCurrentMove ? ply : ply + 1;
          const targetNodeId = this.pgnData.mainline_node_ids[targetPly];
          const targetNode = this.treeNodeMap[targetNodeId];
          const fenBefore = usesCurrentMove ? positions[ply - 1]?.fen : positions[ply]?.fen;
          if (!targetNode || !fenBefore) continue;

          quizPositions.push({
            ply: targetPly,
            fen_before: fenBefore,
            expected_move_san: targetNode.san,
            color: this.normalizeQuizColor(targetNode.color),
            comment: node.comment || null,
          });
        }
        return quizPositions;
      }

      const quizPositions = [];
      // Check starting position (ply = 0) for critical position
      if (positions[0] && (Boolean(positions[0].cp_tag) || this.commentHasCriticalPosition(positions[0].comment))) {
        // Starting position is marked critical, quiz should start from first move
        if (positions.length > 1) {
          const firstPosition = positions[1];
          if (firstPosition) {
            quizPositions.push({
              ply: 1,
              fen_before: positions[0].fen,
              expected_move_san: firstPosition.san,
              color: this.normalizeQuizColor(firstPosition.color),
              comment: positions[0].comment || null,
            });
          }
        }
      }
      // Continue with remaining positions
      for (let ply = 1; ply < positions.length; ply += 1) {
        const position = positions[ply];
        if (!position) continue;
        const isCriticalPosition = Boolean(position.cp_tag) || this.commentHasCriticalPosition(position.comment);
        if (!isCriticalPosition) continue;

        const usesCurrentMove = this.commentMarksCurrentMoveAsCritical(position.comment);
        const targetPly = usesCurrentMove ? ply : ply + 1;
        const targetPosition = positions[targetPly];
        const fenBefore = usesCurrentMove ? positions[ply - 1]?.fen : positions[ply]?.fen;
        if (!targetPosition || !fenBefore) continue;

        quizPositions.push({
          ply: targetPly,
          fen_before: fenBefore,
          expected_move_san: targetPosition.san,
          color: this.normalizeQuizColor(targetPosition.color),
          comment: position.comment || null,
        });
      }
      return quizPositions;
    },

    refreshQuizPositions() {
      this.quizPositions = this.buildQuizPositionsFromCurrentGame();
      if (!this.quizPositions.length && this.activeTab === 'Quiz') {
        this.activeTab = 'PGN';
      }
    },

    initiateQuiz() {
      this.activeTab = 'Quiz';
    },

    handleStartQuiz() {
      this.isQuizActive = true;
      this.stopLiveAnalysis();
    },

    handleStopQuiz() {
      this.isQuizActive = false;
    },

    handleQuizShowPosition(fen) {
      this.fen = fen;
    },

    handleQuizFinished(stats) {
      // Quiz analysis is now handled entirely inside QuizTab.
      // Just mark quiz as no longer blocking the rest of the UI.
      this.isQuizActive = false;
    },

    handleQuizModeChanged(event) {
      // Keep all tabs disabled throughout entire quiz (including results screen)
      // Only re-enable tabs when user explicitly exits quiz mode
      this.quizModeDisablesOtherTabs = event.active;
      if (event.active) {
        this.activeTab = 'Quiz'; // Force tab to stay on Quiz
      } else if (event?.reason === 'exit') {
        // When exiting quiz, reset to the starting position of the PGN
        this.currentMove = 0;
        this.fen = this.currentGameStartFen;
      }
    },

    handleQuizExitFirstMove(event) {
      // Called when exiting quiz mode to return to first move with quiz orientation
      // event.keepFlipped: whether to keep the board flipped (was flipped for Black quiz)
      // event.startingFen: the starting FEN

      // Go to the first move of the game
      this.currentMove = 0;
      this.fen = event.startingFen || this.currentGameStartFen;

      // Apply the orientation from the quiz (keepFlipped = true if Black quiz)
      // The board should remain in whichever orientation the quiz used
      if (event.keepFlipped && !this.boardFlipped) {
        this.flipBoard();
      } else if (!event.keepFlipped && this.boardFlipped) {
        this.flipBoard();
      }

      // Reset board state
      this.resetAnalysisState();
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
      // During active quiz, all moves go through quiz handler
      if (this.isQuizActive) {
        const quizTab = this.$refs.quizTab;
        const fenBefore = this.fen;
        try {
          const chess = new Chess(fenBefore);
          const moveResult = chess.move({
            from: moveInfo.from,
            to: moveInfo.to,
            promotion: moveInfo.promotion || 'q'
          });
          if (moveResult) {
            this.fen = moveResult.fen;  // Show the move on board
            if (quizTab) {
              quizTab.handleUserMove(moveResult.san);
              // If move was wrong (quiz didn't reveal), reset board back to quiz position
              // after a short delay so user can see what they played
              if (!quizTab.isRevealed) {
                setTimeout(() => {
                  if (this.isQuizActive && !quizTab.isRevealed) {
                    this.fen = fenBefore;
                  }
                }, 600);
              }
            }
          }
        } catch (err) {
          console.warn('Invalid quiz move', err);
        }
        return;
      }

      if (!this.pgnData || !this.pgnData.variation_tree) {
        this.createScratchGameFromFen(this.fen);
      }

      // If PGN with variations is loaded, handle move with variation tree
      try {
        const currentFen = typeof this.fen === 'string' ? this.fen : '';
        const matchedNode = Object.values(this.treeNodeMap).find((node) => node?.fen === currentFen) || null;
        const parentNode = (this.currentTreeNode?.fen === currentFen ? this.currentTreeNode : matchedNode) || this.currentTreeNode || this.pgnData.variation_tree;
        const parentNodeId = Number.isInteger(parentNode.id) ? parentNode.id : 0;
        const parentFen = parentNode?.fen || currentFen;
        const fenParts = typeof parentFen === 'string' ? parentFen.trim().split(/\s+/) : [];
        const parentTurn = fenParts[1] === 'b' ? 'b' : 'w';
        const parentFullmove = parseInt(fenParts[5], 10) || 1;
        const parentMainlineIndex = Number.isInteger(parentNode.mainline_index)
          ? parentNode.mainline_index
          : (Number.isInteger(parentNode.anchor_mainline_index) ? parentNode.anchor_mainline_index : this.currentMove);

        // Extract algebraic notation
       let san = moveInfo.san;
       if (!san) {
         try {
           const chess = new Chess(this.fen);
           const moveResult = chess.move({
             from: moveInfo.from,
             to: moveInfo.to,
             promotion: moveInfo.promotion || 'q'
           });
           if (moveResult) {
             san = moveResult.san;
             this.fen = moveResult.fen; // Show the move on board
             if (this.$refs.quizTab) {
               this.$refs.quizTab.handleUserMove(san);
             }
           }
         } catch (err) {
           console.warn("Invalid user move recalculation", err);
           san = null;
         }
       }

       if (!san) return;

       // Check if this move already exists in variations
       if (parentNode.variations && Array.isArray(parentNode.variations)) {
         const existingMove = parentNode.variations.find(v => v.san === san && v.fen === moveInfo.fen);
         if (existingMove) {
           // Move already exists, just navigate to it
           await this.selectTreeNode(existingMove.id);
           return;
         }
       }

       // Create new variation node for this move
       const newPly = Number.isInteger(parentNode.ply)
         ? parentNode.ply + 1
         : ((parentFullmove - 1) * 2) + (parentTurn === 'w' ? 1 : 2);
       const newColor = parentTurn;
       const newMoveNumber = parentFullmove;

       const existingMainlineChild = Array.isArray(parentNode.variations)
         ? parentNode.variations.find((variation) => variation?.is_mainline)
         : null;
       const extendsScratchMainline = Boolean(this.pgnData?.isScratchGame)
         && parentNode?.is_mainline !== false
         && !existingMainlineChild;

       const newId = this.generateNewNodeId();
       const newNode = {
         id: newId,
         san: san,
         move: moveInfo.promotion ? `${moveInfo.from}${moveInfo.to}${moveInfo.promotion}` : `${moveInfo.from}${moveInfo.to}`,
         fen: moveInfo.fen,
         ply: newPly,
         color: newColor,
         move_number: newMoveNumber,
         comment: null,
         starting_comment: null,
         nags: [],
         nag_symbols: [],
         nag_display: null,
         is_mainline: extendsScratchMainline,
         mainline_index: extendsScratchMainline ? parentMainlineIndex + 1 : null,
         anchor_mainline_index: extendsScratchMainline ? parentMainlineIndex + 1 : parentMainlineIndex,
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

       if (this.pgnData?.isScratchGame) {
         this.rebuildScratchGameData();
       }

       await this.selectTreeNode(newId);
      } catch (err) {
        console.error('Error processing move:', err);
        // Fallback: just apply the move to the board
        try {
          this.fen = moveInfo.fen;
          if (this.socket) this.analyzeLive();
        } catch (e) {
          console.warn('Fallback move failed:', e);
        }
      }
    },

    updateNodeNags({ nodeId, nags }) {
      if (!this.pgnData?.variation_tree) return;

      const node = this.treeNodeMap[nodeId];
      if (node) {
        node.nags = nags;
        node.nag_symbols = nags.map(this.nagToSymbol).filter(Boolean);
        node.nag_display = node.nag_symbols.length > 0 ? node.nag_symbols.join(' ') : null;
        // Mark as unsaved whenever NAGs change
        this.hasUnsavedChanges = true;
        if (!this.unsavedNodeIds.includes(nodeId)) {
          this.unsavedNodeIds.push(nodeId);
        }
        if (this.pgnData?.isScratchGame) {
          this.rebuildScratchGameData();
        }
      }
    },

    updateNodeComment({ nodeId, comment }) {
      if (!this.pgnData?.variation_tree) return;

      const node = this.treeNodeMap[nodeId];
      if (node) {
        node.comment = comment || null;
        node.cp_tag = this.commentHasCriticalPosition(node.comment);
        // Mark as unsaved whenever comment changes
        this.hasUnsavedChanges = true;
        if (!this.unsavedNodeIds.includes(nodeId)) {
          this.unsavedNodeIds.push(nodeId);
        }
        if (this.pgnData?.isScratchGame) {
          this.rebuildScratchGameData();
        }
        this.refreshQuizPositions();
      }
    },

    nagToSymbol(nag) {
      const NAG_DISPLAY_MAP = {
        1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!",
        10: "=", 11: "=", 12: "∞", 13: "∞", 14: "+=", 15: "=+",
        16: "+/-", 17: "-/+", 18: "+-", 19: "-+", 20: "+-", 21: "-+",
        22: "⩲", 23: "⩱", 24: "±", 25: "∓", 26: "+-", 27: "-+", 32: "⟳",
        36: "↑", 40: "→", 44: "⇄", 130: "Z", 131: "⩲", 132: "⟳", 133: "⩱",
        136: "↑", 138: "⇄", 140: "∆", 142: "⌓",
        145: "RR", 146: "N"
      };
      return NAG_DISPLAY_MAP[nag] || `$${nag}`;
    },

    async saveChanges() {
      if (!this.gameId && this.pgnData?.isScratchGame) {
        const scratchPgn = this.buildScratchGamePgn();
        if (!scratchPgn.trim()) {
          alert('Nothing to save yet.');
          return;
        }

        try {
          const response = await fetch(buildApiUrl('/games'), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ pgn: scratchPgn }),
          });

          if (!response.ok) {
            const detail = await this.readErrorResponse(response, 'Failed to save new game');
            throw new Error(detail);
          }

          const data = await response.json();
          if (!data.success || !data.id) {
            throw new Error('Failed to create new saved game');
          }

          if (!this.sessionGameIds.includes(data.id)) {
            this.sessionGameIds = [...this.sessionGameIds, data.id];
          }
          await this.fetchGames();
          await this.loadGame(data.id);

          this.hasUnsavedChanges = false;
          this.unsavedNodeIds = [];
          this.backupTreeNodeId = null;
          return;
        } catch (error) {
          console.error('Failed to save new scratch game:', error);
          alert(`Save failed: ${this.stringifyError(error, 'Unknown error')}`);
          return;
        }
      }

      if (this.gameId && this.pgnData?.variation_tree && Array.isArray(this.pgnData.mainline_node_ids)) {
        const annotations = this.pgnData.mainline_node_ids
          .map((nodeId, index) => {
            const ply = index;
            const node = this.treeNodeMap[nodeId];
            if (!node) return null;
            return {
              ply,
              comment: node.comment || null,
              cp_tag: Boolean(node.cp_tag) || this.commentHasCriticalPosition(node.comment),
            };
          })
          .filter(Boolean);

        try {
          const response = await fetch(buildApiUrl(`/games/${this.gameId}/annotations`), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ annotations }),
          });

          if (!response.ok) {
            const detail = await this.readErrorResponse(response, 'Failed to save changes');
            throw new Error(detail);
          }

          const data = await response.json();
          if (!data.success) {
            throw new Error('Failed to save changes');
          }
        } catch (error) {
          console.error('Failed to persist annotations:', error);
          alert(`Save failed: ${this.stringifyError(error, 'Unknown error')}`);
          return;
        }
      }

      this.hasUnsavedChanges = false;
      this.unsavedNodeIds = [];
      this.backupTreeNodeId = null;
      this.refreshQuizPositions();
      // Notify QuizTab that PGN has been saved
      if (this.$refs.quizTab && this.$refs.quizTab.markPGNSaved) {
        this.$refs.quizTab.markPGNSaved();
      }
      // Deselect current node to close inline editor
      this.currentTreeNodeId = 0;
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
      this.refreshQuizPositions();
      // Deselect current node to close inline editor
      this.currentTreeNodeId = 0;
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
        this.activeTab = 'Analysis';
        this.sendAnalysisRequest();
        return;
      }

      this.resetAnalysisState("Connecting to analysis service...");
      if (this.socket) this.socket.close();

      const socketUrl = this.wsUrl("/ws/analyze");
      this.socket = new WebSocket(socketUrl);

       this.socket.onopen = () => {
         this.analysisStatusText = "Live analysis started";
         this.activeTab = 'Analysis';
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
        depth: LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH,
        display_target_depth: LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH,
        worker_target_depth: LIVE_ANALYSIS_WORKER_TARGET_DEPTH,
        display_lag_depth: LIVE_ANALYSIS_DISPLAY_LAG_DEPTH,
      }));
      this.updateAnalysisStatus('Live analysis updated', true);
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
      if (!this.pgnData && !this.fen) return;

      if (this.pgnData?.variation_tree) {
        const nextNode = this.getContinuationChild(this.currentTreeNode);
        if (nextNode?.id != null) {
          await this.showTreeNode(nextNode.id);
        }
        return;
      }

      if (this.pgnData && this.currentMove < this.pgnData.total_moves) {
        this.currentMove++;
        await this.showPosition(this.currentMove);
      }
    },

    async prevMove() {
      if (!this.pgnData && !this.fen) return;

      if (this.pgnData?.variation_tree) {
        const parentNodeId = this.treeParentMap[this.currentTreeNodeId];
        if (Number.isInteger(parentNodeId)) {
          await this.showTreeNode(parentNodeId);
        }
        return;
      }

      if (this.pgnData && this.currentMove > 0) {
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
        this.updateAnalysisStatus(payload.message || "Analysis failed", true);
        console.error("Analysis error:", payload.message || payload);
        return;
      }

      if (payload.type === "status") {
        this.syncAnalysisActivity(payload);
        this.updateAnalysisStatus(this.formatAnalysisStatus(payload, this.statusLabel(payload.status)));
        return;
      }

      if (payload.type === "snapshot") {
        this.syncAnalysisActivity(payload);
        const sourceLabel = payload.source === "database" ? "DB" : "Engine";
        this.updateAnalysisStatus(this.formatAnalysisStatus(payload, sourceLabel));
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

    updateAnalysisStatus(nextStatus, force = false) {
      if (typeof nextStatus !== 'string' || !nextStatus.trim()) return;
      const now = Date.now();
      if (!force) {
        if (nextStatus === this.lastStatusText && (now - this.lastStatusRenderedAt) < this.analysisStatusMinMs) {
          return;
        }
        if ((now - this.lastStatusRenderedAt) < this.analysisStatusMinMs) {
          return;
        }
      }
      this.analysisStatusText = nextStatus;
      this.lastStatusText = nextStatus;
      this.lastStatusRenderedAt = now;
    },

    getCachedAlgebraic(uciMoves, fenString) {
      if (!uciMoves) return "";
      const key = `${fenString}__${uciMoves}`;
      if (Object.prototype.hasOwnProperty.call(this.analysisPvCache, key)) {
        return this.analysisPvCache[key];
      }

      const value = this.convertToAlgebraic(uciMoves, fenString);
      if (Object.keys(this.analysisPvCache).length >= 250) {
        this.analysisPvCache = Object.create(null);
      }
      this.analysisPvCache[key] = value;
      return value;
    },

    renderSnapshot(snapshot) {
      const depth = parseInt(snapshot.depth || 0, 10);
      const lines = Array.isArray(snapshot.lines) ? snapshot.lines : [];
      if (!depth || lines.length === 0) return;

      const depthLines = lines.map((line, idx) => {
        const pvUci = line.pv || "";
        const pvAlgebraic = pvUci ? this.getCachedAlgebraic(pvUci, this.fen) : "";
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
      const now = Date.now();
      const elapsed = now - (this.lastRenderedAt || 0);
      const sameDepth = latestDepth === this.currentAnalysisDepth;
      const requiredDelay = sameDepth ? this.analysisRenderMinMs : this.analysisHoldMs;
      const remainingHold = Math.max(0, requiredDelay - elapsed);

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
              ? this.getCachedAlgebraic(pvUci, this.fen)
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
  grid-template-columns: 60px minmax(430px, 520px) minmax(460px, 700px);
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
  position: relative;
}

.board-settings-anchor {
  position: absolute;
  top: 0;
  left: calc(100% + 12px);
  z-index: 30;
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
  .board-settings-anchor {
    position: static;
    margin-top: 8px;
  }
  .center-stage { grid-column: 2; grid-row: 1; }
  .right-panel { grid-column: 1 / span 2; grid-row: 2; }
}

@media (max-width: 600px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .left-sidebar { grid-column: 1; flex-direction: row; justify-content: center; }
  .board-settings-anchor { width: 100%; }
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

.pgn-quiz-action {
  display: flex;
  justify-content: center;
  margin-top: 15px;
}

.btn-start-quiz {
  background-color: #e91e63;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-size: 14px;
  transition: background-color 0.2s;
}

.btn-start-quiz:hover:not(:disabled) {
  background-color: #c2185b;
}

.btn-start-quiz:active:not(:disabled) {
  background-color: #ad1457;
}

.btn-start-quiz:disabled {
  background-color: #ccc;
  color: #666;
  cursor: not-allowed;
  opacity: 0.7;
}


</style>

