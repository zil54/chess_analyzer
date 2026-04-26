<template>
  <div class="quiz-tab">

    <!-- ── Setup ──────────────────────────────────────────────────────────── -->
    <div v-if="!isQuizStarted && !quizResults && !isLoadingResults" class="quiz-setup">
      <h3>Quiz Mode</h3>
      <p v-if="positions.length === 0" class="no-positions">
        No critical positions found.<br>
        Add <code>{CPosition}</code> to move comments to mark them.
      </p>
      <div v-else>
        <div class="setup-group">
          <label>Play as:</label>
          <div class="radio-group">
            <label><input type="radio" v-model="selectedColor" value="W"> White</label>
            <label><input type="radio" v-model="selectedColor" value="B"> Black</label>
          </div>
        </div>
        <div class="setup-group">
          <label>Time per move (sec):</label>
          <input type="number" v-model.number="timeLimit" min="5" max="300" class="time-input">
        </div>
        <p class="quiz-info">{{ filteredPositions.length }} position(s) for your selection.</p>
        <div v-if="hasUnsavedPGNChanges" class="unsaved-warning">
          ⚠ Please save PGN changes first before starting quiz
        </div>
        <button class="btn-start" @click="startQuiz" :disabled="filteredPositions.length === 0 || hasUnsavedPGNChanges">
          Start Quiz
        </button>
      </div>
    </div>

    <!-- ── Active quiz ────────────────────────────────────────────────────── -->
    <div v-else-if="isQuizStarted" class="quiz-active">
      <div class="quiz-header">
        <div class="quiz-progress">Position {{ currentIdx + 1 }} / {{ _quizPositions.length }}</div>
        <div class="quiz-timer" :class="{ 'timer-low': timer < 10 }">&#9201; {{ timer }}s</div>
      </div>

      <!-- Waiting for a move -->
      <template v-if="!isRevealed">
        <div class="quiz-instruction">Make your move on the board.</div>
        <div class="quiz-idle-note">Stockfish analyzes while you think &mdash; results appear instantly.</div>
        <div class="quiz-controls">
          <button class="btn-stop" @click="stopQuiz">Stop Quiz</button>
          <button class="btn-skip" @click="skipPosition">Skip &rarr;</button>
        </div>
      </template>

      <!-- After a move was submitted -->
      <template v-else>
        <div class="submitted-box">
          <span class="submitted-label">Submitted:</span>
          <strong class="submitted-san">
            {{ formatMoveWithNumber(currentPosition && currentPosition.fen_before, submittedMoveSan) }}
          </strong>
        </div>
        <div class="quiz-controls">
          <button class="btn-stop" @click="stopQuiz">Stop Quiz</button>
          <button v-if="currentIdx < _quizPositions.length - 1" class="btn-next" @click="nextPosition">
            Next Position &rarr;
          </button>
          <button v-else class="btn-finish" @click="finishQuiz">Finish &amp; Analyze</button>
        </div>
      </template>
    </div>

    <!-- ── Loading ────────────────────────────────────────────────────────── -->
    <div v-else-if="isLoadingResults" class="quiz-loading">
      <div class="loading-spinner"></div>
      <p class="loading-text">Compiling results from background analysis...</p>
      <p class="loading-sub">Most positions were analyzed while you played</p>
    </div>

    <!-- ── Results ────────────────────────────────────────────────────────── -->
    <div v-else-if="quizResults" class="quiz-results">

      <!-- Score banner -->
      <div class="score-banner">
        <div class="score-pct">{{ quizResults.score_percentage }}%</div>
        <div class="score-detail">
          <span class="sd-full">&#10003; {{ quizResults.full_answers }} correct</span>
          <span class="sd-sep">&middot;</span>
          <span class="sd-partial" v-if="quizResults.partial_answers > 0">&#8856; {{ quizResults.partial_answers }} partial</span>
          <span class="sd-sep" v-if="quizResults.partial_answers > 0">&middot;</span>
          <span class="sd-fail">&#10007; {{ quizResults.fail_answers }} incorrect</span>
          <template v-if="quizResults.skipped_answers > 0">
            <span class="sd-sep">&middot;</span>
            <span class="sd-skip">&mdash; {{ quizResults.skipped_answers }} skipped</span>
          </template>
        </div>
        <div class="score-credit" v-if="quizResults.total_credit != null">
          {{ quizResults.total_credit.toFixed(2) }} / {{ quizResults.total_questions }} pts
        </div>
      </div>

      <p v-if="quizResults.error" class="results-error">&#9888; {{ quizResults.error }}</p>

      <!-- Per-position cards -->
      <div class="results-list">
        <div
          v-for="(entry, idx) in quizResults.entries"
          :key="idx"
          class="rcard"
          :class="{
            'rcard-pass':    entry.result_type === 'full' || (!entry.analysis && entry.pass),
            'rcard-partial': entry.result_type === 'partial',
            'rcard-fail':    entry.attempted && !entry.pass,
            'rcard-skipped': !entry.attempted
          }"
        >
          <!-- Card header row -->
          <div class="rcard-head">
            <span class="rcard-num rcard-num-click"
              @click="$emit('jump-to-ply', entry.ply)"
              style="cursor: pointer; text-decoration: underline;"
              title="Click to load this position in the board"
            >
              Position {{ idx + 1 }}
            </span>
            <span class="rcard-badge"
              :class="{
                'badge-full':    entry.result_type === 'full' || (!entry.analysis && entry.pass),
                'badge-partial': entry.result_type === 'partial',
                'badge-fail':    entry.attempted && !entry.pass,
                'badge-skipped': !entry.attempted
              }"
            >
              <template v-if="entry.result_type === 'full' || (!entry.analysis && entry.pass)">&#10003; Correct</template>
              <template v-else-if="entry.result_type === 'partial'">&#8856; Partial ({{ (entry.analysis ? entry.analysis.credit : entry.credit || 0).toFixed(2) }})</template>
              <template v-else-if="entry.attempted">&#10007; Incorrect</template>
              <template v-else>&mdash; Skipped</template>
            </span>
          </div>

          <!-- Analysis side by side -->
          <div class="rcard-body">
            <!-- Move info & SF analysis -->
            <div class="rcard-analysis">

              <!-- Move comparison -->
              <div class="move-block">
                <div class="move-row">
                  <span class="mlabel">Your move:</span>
                  <span class="msan" :class="{ 'msan-pass': entry.pass, 'msan-fail': entry.attempted && !entry.pass, 'msan-none': !entry.attempted }">
                    {{ entry.user_move_san ? formatMoveWithNumber(entry.fen_before, entry.user_move_san) : '(not played)' }}
                  </span>
                </div>
                <div class="move-row">
                  <span class="mlabel">Game move:</span>
                  <span class="msan">{{ formatMoveWithNumber(entry.fen_before, entry.expected_move_san || entry.game_move_san) }}</span>
                </div>
                <div v-if="entry.analysis && entry.analysis.stockfish.best_move_san" class="move-row">
                  <span class="mlabel">SF best:</span>
                  <span class="msan msan-sf"
                    :class="{ 'msan-sf-same': entry.analysis.stockfish.best_move_san === (entry.expected_move_san || entry.game_move_san) }"
                  >{{ formatMoveWithNumber(entry.fen_before, entry.analysis.stockfish.best_move_san) }}</span>
                </div>
              </div>

               <!-- Feedback line -->
               <div v-if="entry.analysis" class="feedback-line">{{ entry.analysis.feedback }}</div>
               <div v-else-if="!entry.attempted" class="feedback-line skipped-note">
                 Skipped &mdash; solution was <strong>{{ entry.expected_move_san }}</strong>
               </div>

               <!-- Eval swing display (show for any analyzed move with eval_swing_cp) -->
               <div v-if="entry.analysis && entry.analysis.eval_swing_cp !== null && entry.analysis.eval_swing_cp !== undefined" class="eval-swing-info">
                 <span class="eval-swing-label">Evaluation swing:</span>
                 <span class="eval-swing-value">{{ entry.analysis.eval_swing_cp.toFixed(0) }} cp</span>
               </div>

             </div>
           </div>
         </div>
      </div>

      <div class="results-actions">
        <button @click="saveQuizResults" :disabled="isSaving" class="btn-save">
          {{ isSaving ? '💾 Saving...' : '💾 Save Results' }}
        </button>
        <button @click="exportToPDF" class="btn-export" title="Export results to PDF">
          📄 Export to PDF
        </button>
        <button @click="redoQuiz" class="btn-redo">🔄 Redo Same Quiz</button>
        <button @click="exitQuizMode" class="btn-exit">✕ Exit Quiz Mode</button>
      </div>
    </div>

   </div>

   <!-- ── Fixed board tooltip (escapes overflow:auto clipping) ──────────── -->
   <teleport to="body">
    <div
      v-if="hoveredPositionIdx !== null && quizResults && quizResults.entries[hoveredPositionIdx]"
      class="pos-tooltip-fixed"
      :style="{ left: tooltipX + 'px', top: tooltipY + 'px' }"
    >
      <MiniBoard :fen="quizResults.entries[hoveredPositionIdx].fen_before" :size="180" />
    </div>
  </teleport>

</template>

<script>
import { h } from 'vue';
import { Chess } from 'chess.js';

// ── MiniBoard: render-function component (no runtime compiler needed) ────────
const PIECE_UNICODE = {
  wK: '\u2654', wQ: '\u2655', wR: '\u2656', wB: '\u2657', wN: '\u2658', wP: '\u2659',
  bK: '\u265A', bQ: '\u265B', bR: '\u265C', bB: '\u265D', bN: '\u265E', bP: '\u265F',
};

const MiniBoard = {
  name: 'MiniBoard',
  props: {
    fen:  { type: String, required: true },
    size: { type: Number, default: 120 },
  },
  render() {
    const sqSize = Math.floor(this.size / 8);
    const cells  = [];
    try {
      const chess = new Chess(this.fen);
      const board = chess.board();
      for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
          const sq     = board[r][c];
          const light  = (r + c) % 2 === 0;
          const piece  = sq ? (PIECE_UNICODE[sq.color + sq.type.toUpperCase()] || '') : '';
          const pColor = sq ? sq.color : null;
          cells.push(h('div', {
            key: `${r}${c}`,
            style: {
              width: sqSize + 'px', height: sqSize + 'px',
              fontSize: (sqSize * 0.72) + 'px',
              background: light ? '#f0f0f0' : '#505050',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxSizing: 'border-box', lineHeight: '1',
            },
          }, piece ? [h('span', {
            style: pColor === 'w'
              ? 'color:#fff;text-shadow:0 0 2px #000,0 0 1px #000;'
              : 'color:#000;text-shadow:0 0 2px #ccc;',
          }, piece)] : []));
        }
      }
    } catch { /* invalid FEN – render empty board */ }
    return h('div', {
      style: {
        display: 'flex', flexWrap: 'wrap',
        border: '2px solid #333', boxSizing: 'border-box',
        overflow: 'hidden', borderRadius: '2px',
        width: this.size + 'px', height: this.size + 'px',
      },
    }, cells);
  },
};

export default {
  name: 'QuizTab',
  props: {
    positions:   { type: Array,  required: true },
    gameId:      { type: Number, required: false, default: null },
    apiBaseUrl:  { type: String, required: false, default: '' },
  },
   emits: ['start-quiz', 'stop-quiz', 'show-position', 'quiz-finished', 'correct-move', 'jump-to-ply', 'quiz-mode-changed', 'flip-board'],

  data() {
    return {
      isQuizStarted: false,
      selectedColor: 'W',
      timeLimit: 30,
      currentIdx: 0,
      timer: 0,
      timerInterval: null,
      isRevealed:       false,
      submittedMoveSan: null,   // move the user played (null = not yet / skipped)
      // silent tracking
      positionResults: {},   // keyed by idx
      // results
      quizResults: null,
      isLoadingResults: false,
      isSaving: false,
      // PGN save tracking
      lastSavedGameId: null,
      lastSavedPositionCount: 0,
      // snapshot of positions for this quiz run
      _quizPositions: [],
      // hover state for position tooltip
      hoveredPositionIdx: null,
      tooltipX: 0,
      tooltipY: 0,
      // background analysis cache
      analysisCache: {},   // keyed by ply, stores backend analysis results
      analyzedPlies: new Set(),  // track which plies have been analyzed
    };
  },

  mounted() {
    this.loadSavedQuizResults();
  },

  computed: {
    filteredPositions() {
      if (this.selectedColor === 'Both' || this.selectedColor === 'W') {
        return this.positions.filter(p => p.color === 'W');
      }
      return this.positions.filter(p => p.color === this.selectedColor);
    },
    currentPosition() {
      return this._quizPositions[this.currentIdx] || null;
    },
    hasUnsavedPGNChanges() {
      // If we don't have a saved game ID yet, or if positions count changed, we need to save first
      return this.gameId !== this.lastSavedGameId ||
             this.positions.length !== this.lastSavedPositionCount;
    },
  },

  watch: {
    positions(newPositions, oldPositions) {
      // When positions change (new PGN uploaded), reset quiz results
      if (JSON.stringify(newPositions) !== JSON.stringify(oldPositions)) {
        this.quizResults = null;
        this.isQuizStarted = false;
        this.positionResults = {};
        this.currentIdx = 0;
        this.isRevealed = false;
        this.submittedMoveSan = null;
        this._quizPositions = [];
      }
    },
    gameId(newGameId) {
      // When game changes, mark that we need to save before starting new quiz
      if (newGameId !== this.lastSavedGameId) {
        this.quizResults = null;
        this.isQuizStarted = false;
      }
    },
  },

   methods: {
     // ── Lifecycle ──────────────────────────────────────────────────────────
     startQuiz() {
      this._quizPositions   = [...this.filteredPositions];
      this.isQuizStarted    = true;
      this.currentIdx       = 0;
      this.isRevealed       = false;
      this.submittedMoveSan = null;
      this.positionResults  = {};
      this.quizResults      = null;
      // Flip board to match the selected color (Black flips the board)
      if (this.selectedColor === 'B') {
        this.$emit('flip-board');
      }
      this.$emit('start-quiz');
      this.$emit('quiz-mode-changed', { active: true });
      this.setupPosition();
     },

     stopQuiz() {
      this.isQuizStarted = false;
      this.clearTimer();
      // Reset board orientation when stopping quiz
      if (this.selectedColor === 'B') {
        this.$emit('flip-board');
      }
      this.$emit('stop-quiz');
      this.$emit('quiz-mode-changed', { active: false });
     },

    setupPosition() {
      if (!this.currentPosition) return;
      this.isRevealed       = false;
      this.submittedMoveSan = null;
      this.timer = this.timeLimit;
      this.$emit('show-position', this.currentPosition.fen_before);
      this.clearTimer();
      this.timerInterval = setInterval(() => {
        this.timer > 0 ? this.timer-- : this.onTimeout();
      }, 1000);

      // Start background analysis for this position while user thinks about move
      this.analyzePositionInBackground();
    },

    clearTimer() {
      if (this.timerInterval) { clearInterval(this.timerInterval); this.timerInterval = null; }
    },

    onTimeout() {
      this.clearTimer();
      this.skipPosition();
    },

     // ── Move handling (called by Analyzer on user board move) ────
     handleUserMove(moveSan) {
      if (!this.isQuizStarted || this.isRevealed) return;
      const pos = this.currentPosition;
      if (!pos) return;

      const uciMove   = this._sanToUci(pos.fen_before, moveSan);
      const isCorrect = moveSan === pos.expected_move_san;

      this.positionResults[this.currentIdx] = {
        positionIndex:     this.currentIdx,
        fen_before:        pos.fen_before,
        expected_move_san: pos.expected_move_san,
        user_move_san:     moveSan,
        user_move_uci:     uciMove,
        ply:               pos.ply,
        attempted:         true,
        correct:           isCorrect,
        revealed:          true,
      };

      this.submittedMoveSan = moveSan;
      this.clearTimer();
      this.isRevealed = true;
      if (isCorrect) this.$emit('correct-move');
    },

     // Skip current position without answering → go directly to next
    skipPosition() {
      if (!this.positionResults[this.currentIdx]) {
        const pos = this.currentPosition;
        if (pos) {
          this.positionResults[this.currentIdx] = {
            positionIndex:     this.currentIdx,
            fen_before:        pos.fen_before,
            expected_move_san: pos.expected_move_san,
            user_move_san:     null,
            user_move_uci:     null,
            ply:               pos.ply,
            attempted:         false,
            correct:           false,
            revealed:          false,
          };
        }
      }
      this.clearTimer();
      if (this.currentIdx < this._quizPositions.length - 1) {
        this.currentIdx++;
        this.setupPosition();
      } else {
        this.finishQuiz();
      }
    },

    nextPosition() {
      if (this.currentIdx < this._quizPositions.length - 1) {
        this.currentIdx++;
        this.setupPosition();
      }
    },

    finishQuiz() {
      this.isQuizStarted = false;
      this.clearTimer();
      this.$emit('stop-quiz');
      this.submitQuizForAnalysis();
    },

     // ── Backend analysis ──────────────────────────────────────────
     async submitQuizForAnalysis() {
      const allEntries = this._quizPositions.map((pos, idx) => {
        return this.positionResults[idx] || {
          positionIndex: idx,
          fen_before: pos.fen_before,
          expected_move_san: pos.expected_move_san,
          user_move_san: null,
          user_move_uci: null,
          ply: pos.ply,
          attempted: false,
          correct: false,
          revealed: false,
        };
      });

      const backendPayload = allEntries
        .filter(e => e.user_move_uci)
        .map(e => ({
          ply: e.ply,
          fen_before: e.fen_before,
          expected_move: e.expected_move_san,
          user_move: e.user_move_uci,
        }));

      this.isLoadingResults = true;
      let backendResultsMap = {};

      try {
        if (this.gameId && backendPayload.length > 0) {
          const url = `${this.apiBaseUrl}/games/${this.gameId}/quiz/results`;
          const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ responses: backendPayload, depth: 20, time_limit: 0.6 }),
          });
          if (resp.ok) {
            const data = await resp.json();
            for (const r of (data.results || [])) {
              backendResultsMap[r.ply] = r;
            }
          } else {
            console.warn('Quiz analysis HTTP error', resp.status);
          }
        }
      } catch (err) {
        console.error('Quiz analysis fetch failed:', err);
      } finally {
        this.isLoadingResults = false;
      }

      // Merge backend results into entries
      const mergedEntries = allEntries.map(e => {
        const backendR = backendResultsMap[e.ply] || null;
        return {
          ...e,
          result_type: backendR ? backendR.result_type : (e.correct ? 'full' : 'fail'),
          credit:      backendR ? backendR.credit       : (e.correct ? 1.0   : 0.0),
          pass:        backendR ? backendR['pass']       : e.correct,
          analysis: backendR
            ? {
                feedback:         backendR.feedback,
                credit:           backendR.credit,
                result_type:      backendR.result_type,
                eval_swing_cp:    backendR.eval_swing_cp,
                expected_move_san: backendR.game_move_san || e.expected_move_san,
                game_move_san:    backendR.game_move_san,
                game_differs_from_sf: backendR.game_differs_from_sf,
                stockfish:        backendR.stockfish,
              }
            : null,
        };
      });

      const passCount    = mergedEntries.filter(e => e.pass).length;
      const fullCount    = mergedEntries.filter(e => e.result_type === 'full').length;
      const partialCount = mergedEntries.filter(e => e.result_type === 'partial').length;
      const attemptedCnt = mergedEntries.filter(e => e.attempted).length;
      const failCount    = mergedEntries.filter(e => e.attempted && !e.pass).length;
      const totalCredit  = mergedEntries.reduce((s, e) => s + (e.credit || 0), 0);

      this.quizResults = {
        score_percentage: attemptedCnt > 0 ? Math.round((totalCredit / attemptedCnt) * 100) : 0,
        pass_answers:    passCount,
        full_answers:    fullCount,
        partial_answers: partialCount,
        fail_answers:    failCount,
        skipped_answers: mergedEntries.length - attemptedCnt,
        total_questions: mergedEntries.length,
        total_credit:    Math.round(totalCredit * 100) / 100,
        entries: mergedEntries,
        error: (backendPayload.length === 0)
          ? 'No moves played – engine analysis unavailable.'
          : (!this.gameId ? 'No game ID – engine analysis unavailable.' : null),
      };

      // Keep tabs disabled throughout results screen (active: true maintains disabled state)
      this.$emit('quiz-mode-changed', { active: true });
      this.$emit('quiz-finished', { completed: passCount, total: mergedEntries.length });
    },

     // ── Helpers ────────────────────────────────────────────────────
     onPositionHover(idx, e) {
      this.hoveredPositionIdx = idx;
      this.tooltipX = e.clientX + 18;
      this.tooltipY = Math.max(10, e.clientY - 90);
    },

    formatMoveWithNumber(fen, san) {
      if (!san) return '';
      if (!fen) return san;
      try {
        const parts = fen.split(' ');
        const side = parts[1]; // 'w' or 'b'
        const moveNum = parseInt(parts[5], 10) || 1;
        return side === 'w' ? `${moveNum}. ${san}` : `${moveNum}...${san}`;
      } catch {
        return san;
      }
    },

    _sanToUci(fen, san) {
      try {
        const b = new Chess(fen);
        const m = b.move(san);
        return m ? m.from + m.to + (m.promotion || '') : null;
      } catch { return null; }
    },

    formatEval(scoreCp, scoreMate) {
      if (scoreMate !== null && scoreMate !== undefined) {
        return scoreMate > 0 ? `#${scoreMate}` : `#-${Math.abs(scoreMate)}`;
      }
      if (scoreCp === null || scoreCp === undefined) return '?';
      const v = (scoreCp / 100).toFixed(2);
      return scoreCp >= 0 ? `+${v}` : `${v}`;
    },

    evalToNag(scoreCp, scoreMate) {
      if (scoreMate !== null && scoreMate !== undefined) {
        return scoreMate > 0 ? `#${scoreMate}` : `#-${Math.abs(scoreMate)}`;
      }
      if (scoreCp === null || scoreCp === undefined) return '?';
      const cp = scoreCp;
      if (Math.abs(cp) < 25)   return '=';
      if (cp >= 25  && cp < 100)  return '⩲';
      if (cp <= -25 && cp > -100) return '⩱';
      if (cp >= 100 && cp < 300)  return '±';
      if (cp <= -100 && cp > -300) return '∓';
      if (cp >= 300)  return '+−';
      return '−+';
    },

     redoQuiz() {
       this.positionResults  = {};
       this.quizResults      = null;
       this.currentIdx       = 0;
       this.isRevealed       = false;
       this.submittedMoveSan = null;
       this._quizPositions   = [...this.filteredPositions];
       this.isQuizStarted    = true;
       // Flip board to match the selected color (Black flips the board)
       if (this.selectedColor === 'B') {
         this.$emit('flip-board');
       }
       this.$emit('start-quiz');
       this.setupPosition();
     },

    resetQuiz() {
      this.positionResults  = {};
      this.quizResults      = null;
      this.currentIdx       = 0;
      this.isQuizStarted    = false;
      this.isRevealed       = false;
      this.submittedMoveSan = null;
      this._quizPositions   = [];
    },

     exitQuizMode() {
       // Clear all quiz state and return to normal
       this.positionResults  = {};
       this.quizResults      = null;
       this.currentIdx       = 0;
       this.isQuizStarted    = false;
       this.isRevealed       = false;
       this.submittedMoveSan = null;
       this._quizPositions   = [];
       // Reset board orientation if it was flipped for Black
       if (this.selectedColor === 'B') {
         this.$emit('flip-board');
       }
       // Emit that we're exiting quiz mode (other tabs should be enabled)
       this.$emit('quiz-mode-changed', { active: false });
       // Reset board to starting position but keep PGN view at current move
       this.$emit('show-position', 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
     },

    exportToPDF() {
      // TODO: Implement PDF export
      alert('📄 PDF export feature coming soon!');
    },

    markPGNSaved() {
      // Call this from parent when PGN save is complete
      this.lastSavedGameId = this.gameId;
      this.lastSavedPositionCount = this.positions.length;
    },

    setQuizResponses() {},  // compat stub

    // ── Persistence methods ──
    async loadSavedQuizResults() {
      if (!this.gameId) return;
      try {
        const url = `${this.apiBaseUrl}/games/${this.gameId}/quiz/results`;
        const resp = await fetch(url);
        if (resp.ok) {
          const data = await resp.json();
          if (data.results && data.results.entries && data.results.entries.length > 0) {
            this.quizResults = {
              score_percentage: data.results.score_percentage,
              pass_answers: 0,
              full_answers: data.results.full_answers,
              partial_answers: data.results.partial_answers,
              fail_answers: data.results.fail_answers,
              skipped_answers: data.results.skipped_answers,
              total_questions: data.results.total_questions,
              total_credit: data.results.total_credit,
              entries: data.results.entries,
              error: null,
            };
          }
        }
      } catch (err) {
        console.warn('Could not load saved quiz results:', err);
      }
    },

    async saveQuizResults() {
      if (!this.gameId || !this.quizResults) {
        alert('Cannot save: no game ID or no quiz results');
        return;
      }

      this.isSaving = true;
      try {
        const url = `${this.apiBaseUrl}/games/${this.gameId}/quiz/results`;
        const resp = await fetch(url, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            score_percentage: this.quizResults.score_percentage,
            total_questions: this.quizResults.total_questions,
            full_answers: this.quizResults.full_answers,
            partial_answers: this.quizResults.partial_answers,
            fail_answers: this.quizResults.fail_answers,
            skipped_answers: this.quizResults.skipped_answers,
            total_credit: this.quizResults.total_credit,
            entries: this.quizResults.entries,
          }),
        });

        if (resp.ok) {
          const data = await resp.json();
          alert('✓ Quiz results saved successfully!');
          // Optionally reload to ensure UI reflects saved state
          if (data.results) {
            this.quizResults.entries = data.results.entries || this.quizResults.entries;
          }
        } else {
          alert('✗ Failed to save quiz results');
        }
      } catch (err) {
        console.error('Error saving quiz results:', err);
        alert('✗ Error saving quiz results: ' + err.message);
      } finally {
        this.isSaving = false;
      }
    },

    // ── Background analysis (runs during quiz) ────
    async analyzePositionInBackground() {
      const pos = this.currentPosition;
      if (!pos || this.analyzedPlies.has(pos.ply) || !this.gameId) return;

      // Mark as being analyzed to avoid duplicate requests
      this.analyzedPlies.add(pos.ply);

      try {
        const url = `${this.apiBaseUrl}/games/${this.gameId}/quiz/results`;
        const payload = {
          responses: [{
            ply: pos.ply,
            fen_before: pos.fen_before,
            expected_move: pos.expected_move_san,
            user_move: this._sanToUci(pos.fen_before, pos.expected_move_san) || '',
          }],
          depth: 20,
          time_limit: 0.6,
        };

        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (resp.ok) {
          const data = await resp.json();
          if (data.results && data.results.length > 0) {
            this.analysisCache[pos.ply] = data.results[0];
          }
        }
      } catch (err) {
        console.warn('Background analysis failed for ply', pos.ply, err);
      }
    },

  },

  beforeUnmount() { this.clearTimer(); },
};
</script>

<style scoped>
/* ── Global ─────────────────────────────────────────────── */
.quiz-tab { padding: 14px; display: flex; flex-direction: column; gap: 14px; text-align: left; font-size: 0.91em; }
/* ── Setup ──────────────────────────────────────────────── */
.setup-group  { display: flex; flex-direction: column; gap: 5px; margin-bottom: 14px; }
.radio-group  { display: flex; gap: 14px; }
.time-input   { width: 72px; }
.quiz-info    { color: #555; font-size: 0.88em; margin: 0; }
.unsaved-warning { color: #e65100; background: #fff3e0; padding: 8px 12px; border-radius: 4px; font-size: 0.88em; margin: 8px 0; border-left: 4px solid #ff9800; }
.no-positions { color: #888; font-style: italic; }
.btn-start { background: #1976d2; color: #fff; border: none; border-radius: 5px; padding: 10px 18px; font-weight: bold; cursor: pointer; width: 100%; }
.btn-start:disabled { background: #bdbdbd; cursor: not-allowed; }
/* ── Active quiz ────────────────────────────────────────── */
.quiz-header    { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
.timer-low      { color: #e53935; }
.quiz-instruction { color: #444; margin: 6px 0 2px; font-size: 1em; }
.quiz-idle-note { font-size: 0.78em; color: #888; font-style: italic; margin: 0; }
.quiz-controls  { display: flex; gap: 8px; margin-top: 10px; }
.btn-stop   { background: #9e9e9e; color: #fff; border: none; border-radius: 4px; padding: 7px 14px; cursor: pointer; }
.btn-skip   { background: #f57c00; color: #fff; border: none; border-radius: 4px; padding: 7px 14px; cursor: pointer; flex: 1; font-weight: bold; }
.btn-next   { background: #43a047; color: #fff; border: none; border-radius: 4px; padding: 7px 14px; cursor: pointer; flex: 1; font-weight: bold; }
.btn-finish { background: #1976d2; color: #fff; border: none; border-radius: 4px; padding: 7px 14px; cursor: pointer; flex: 1; font-weight: bold; }
.submitted-box {
  margin-top: 12px; padding: 11px 14px;
  background: #e8f5e9; border-left: 5px solid #43a047; border-radius: 6px;
  display: flex; align-items: baseline; gap: 8px;
}
.submitted-label { font-size: 0.85em; color: #555; font-weight: 600; flex-shrink: 0; }
.submitted-san   { font-family: 'Courier New', monospace; font-size: 1.1em; color: #1b5e20; }
/* ── Loading ────────────────────────────────────────────── */
.quiz-loading { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 20px; }
.loading-spinner { width: 36px; height: 36px; border: 4px solid #e0e0e0; border-top-color: #1976d2; border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { font-weight: bold; color: #333; margin: 0; }
.loading-sub  { color: #888; font-size: 0.85em; margin: 0; }
/* ── Results ────────────────────────────────────────────── */
.quiz-results { display: flex; flex-direction: column; gap: 14px; }
.score-banner {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 16px 24px; background: linear-gradient(135deg,#1565c0,#42a5f5);
  color: #fff; border-radius: 10px;
}
.score-pct    { font-size: 2.8em; font-weight: bold; line-height: 1; }
.score-detail { display: flex; gap: 7px; flex-wrap: wrap; justify-content: center; font-size: 0.88em; opacity: .9; }
.score-credit { font-size: 0.85em; opacity: .8; margin-top: 2px; }
.sd-sep     { opacity: .5; }
.sd-full    { color: #a5d6a7; }
.sd-partial { color: #ffe082; }
.sd-fail    { color: #ef9a9a; }
.sd-skip    { color: #b0bec5; }
.results-error { padding: 8px 12px; background: #fff3e0; color: #e65100; border-radius: 4px; font-size: 0.88em; }
.results-list  { display: flex; flex-direction: column; gap: 12px; max-height: 70vh; overflow-y: auto; padding-right: 4px; }
.results-list::-webkit-scrollbar { width: 8px; }
.results-list::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
.results-list::-webkit-scrollbar-thumb { background: #bdbdbd; border-radius: 4px; }
.results-list::-webkit-scrollbar-thumb:hover { background: #9e9e9e; }
.rcard         { border: 1px solid #ddd; border-radius: 8px; padding: 10px 12px; background: #fafafa; }
.rcard-pass    { border-left: 5px solid #43a047; background: #f1f8f5; }
.rcard-partial { border-left: 5px solid #fbc02d; background: #fffde7; }
.rcard-fail    { border-left: 5px solid #e53935; background: #fdf4f4; }
.rcard-skipped { border-left: 5px solid #bdbdbd; background: #f5f5f5; }
.rcard-head  { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.rcard-num   { font-weight: bold; color: #1565c0; cursor: default; text-decoration: underline dotted #90caf9; user-select: none; }
.rcard-badge { font-size: 0.8em; font-weight: bold; padding: 4px 10px; border-radius: 12px; }
.badge-full    { background: #c8e6c9; color: #1b5e20; }
.badge-partial { background: #fff9c4; color: #f57f17; }
.badge-fail    { background: #ffcdd2; color: #b71c1c; }
.badge-skipped { background: #e0e0e0; color: #616161; }
.rcard-body      { display: flex; flex-direction: column; gap: 10px; }
.rcard-analysis  { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.move-block { display: flex; flex-direction: column; gap: 3px; }
.move-row   { display: flex; align-items: center; gap: 6px; }
.mlabel     { min-width: 76px; font-weight: 600; color: #666; font-size: 0.85em; flex-shrink: 0; }
.msan       { font-family: 'Courier New', monospace; font-weight: bold; font-size: 1em; }
.msan-pass  { color: #2e7d32; }
.msan-fail  { color: #c62828; }
.msan-sf    { color: #1565c0; }
.msan-sf-same { color: #2e7d32; }
.msan-none  { color: #999; font-style: italic; font-weight: normal; font-family: inherit; }
.feedback-line { font-size: 0.85em; color: #333; line-height: 1.4; }
.skipped-note  { color: #777; font-style: italic; }
.eval-swing-info { font-size: 0.8em; padding: 6px 8px; background: #fff3e0; border-left: 3px solid #ff9800; border-radius: 3px; margin: 6px 0; display: flex; align-items: center; gap: 8px; }
.eval-swing-label { font-weight: 600; color: #e65100; flex-shrink: 0; }
.eval-swing-value { font-family: 'Courier New', monospace; font-weight: bold; color: #d84315; }
.sf-title { font-size: 0.8em; font-weight: bold; color: #1565c0; margin-top: 2px; }
.sf-lines { display: flex; flex-direction: column; gap: 3px; margin-top: 4px; }
.sf-line-row { display: flex; gap: 6px; align-items: baseline; font-size: 0.8em; background: #f5f5f5; border-radius: 4px; padding: 3px 6px; }
.sf-line-best  { background: #e8eaf6; }
.sf-eval-badge { flex-shrink: 0; font-weight: bold; min-width: 46px; font-size: 0.95em; color: #1565c0; }
.sf-nag-badge  { flex-shrink: 0; font-weight: bold; min-width: 22px; font-size: 1em; color: #555; }
.sf-pv         { color: #444; font-family: 'Courier New', monospace; font-size: 0.93em; word-break: break-word; }
.results-actions { display: flex; gap: 10px; padding-top: 12px; border-top: 1px solid #e0e0e0; }
.btn-save, .btn-redo, .btn-new, .btn-export, .btn-exit { flex: 1; padding: 10px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 0.9em; }
.btn-save       { background: #1565c0; color: #fff; }
.btn-save:hover { background: #1551b0; }
.btn-save:disabled { background: #bdbdbd; cursor: not-allowed; }
.btn-redo       { background: #1976d2; color: #fff; }
.btn-redo:hover { background: #1565c0; }
.btn-export     { background: #f57c00; color: #fff; }
.btn-export:hover { background: #e65100; }
.btn-exit       { background: #d32f2f; color: #fff; }
.btn-exit:hover { background: #c62828; }
.btn-new        { background: #757575; color: #fff; }
.btn-new:hover  { background: #616161; }
.btn-new        { background: #757575; color: #fff; }
.btn-new:hover  { background: #616161; }
</style>
<!-- Global style for teleported tooltip (must NOT be scoped) -->
<style>
.pos-tooltip-fixed {
  position: fixed; z-index: 9999;
  background: #fff; border: 2px solid #424242;
  border-radius: 6px; padding: 4px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.4);
  pointer-events: none;
}
</style>
