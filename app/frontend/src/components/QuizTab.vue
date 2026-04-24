<template>
  <div class="quiz-tab">
    <div v-if="!isQuizStarted" class="quiz-setup">
      <h3>Quiz Mode</h3>
      <p v-if="positions.length === 0" class="no-positions">
        No critical positions found in this game. <br>
        Add {CPosition} in comments to mark them.
      </p>
      <div v-else>
        <div class="setup-group">
          <label>Play as:</label>
          <div class="radio-group">
            <label><input type="radio" v-model="selectedColor" value="W"> White</label>
            <label><input type="radio" v-model="selectedColor" value="B"> Black</label>
            <label><input type="radio" v-model="selectedColor" value="Both"> Both</label>
          </div>
        </div>
        <div class="setup-group">
          <label>Time per move (sec):</label>
          <input type="number" v-model.number="timeLimit" min="5" max="300">
        </div>
        <p class="quiz-info">
          Found {{ filteredPositions.length }} positions for your choice.
        </p>
        <button
          class="btn-start"
          @click="startQuiz"
          :disabled="filteredPositions.length === 0"
        >
          Start Quiz
        </button>
      </div>
    </div>

    <div v-else class="quiz-active">
      <div class="quiz-header">
        <div class="quiz-progress">
          Progress: {{ currentIdx + 1 }} / {{ filteredPositions.length }}
        </div>
        <div class="quiz-timer" :class="{ 'timer-low': timer < 10 }">
          Time: {{ timer }}s
        </div>
      </div>

      <div class="quiz-stats">
        Completed: {{ completedCount }}
      </div>

      <div class="quiz-controls">
        <button class="btn-stop" @click="stopQuiz">Stop Quiz</button>
        <button class="btn-reveal" @click="revealSolution" :disabled="isRevealed">Show Solution</button>
      </div>

      <div v-if="feedback" class="quiz-feedback" :class="feedbackClass">
        {{ feedback }}
      </div>

      <div v-if="isRevealed" class="solution-box">
        Solution: <strong>{{ currentPosition.expected_move_san }}</strong>
        <p v-if="currentPosition.comment" class="solution-comment">{{ currentPosition.comment }}</p>
        <button v-if="currentIdx < filteredPositions.length - 1" @click="nextPosition" class="btn-next">Next Position</button>
        <button v-else @click="finishQuiz" class="btn-finish">Finish Quiz</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'QuizTab',
  props: {
    positions: {
      type: Array,
      required: true
    },
    gameId: {
      type: Number,
      required: false
    }
  },
  emits: ['start-quiz', 'stop-quiz', 'show-position', 'quiz-finished', 'correct-move'],
  data() {
    return {
      isQuizStarted: false,
      selectedColor: 'Both',
      timeLimit: 30,
      currentIdx: 0,
      timer: 0,
      timerInterval: null,
      completedCount: 0,
      isRevealed: false,
      feedback: "",
    };
  },
  computed: {
    filteredPositions() {
      if (this.selectedColor === 'Both') return this.positions;
      return this.positions.filter(p => p.color === this.selectedColor);
    },
    currentPosition() {
      return this.filteredPositions[this.currentIdx];
    },
    feedbackClass() {
      if (!this.feedback) return '';
      if (this.feedback.includes("Correct")) return "feedback-success";
      if (this.feedback.includes("Not quite") || this.feedback.includes("Time's up")) return "feedback-error";
      return "feedback-info";
    }
  },
  methods: {
    startQuiz() {
      this.isQuizStarted = true;
      this.currentIdx = 0;
      this.completedCount = 0;
      this.isRevealed = false;
      this.feedback = "";
      this.$emit('start-quiz');
      this.setupPosition();
    },
    stopQuiz() {
      this.isQuizStarted = false;
      this.clearTimer();
      this.$emit('stop-quiz');
    },
    setupPosition() {
      this.isRevealed = false;
      this.feedback = "Find the best move!";
      this.timer = this.timeLimit;
      this.$emit('show-position', this.currentPosition.fen_before);

      this.clearTimer();
      this.timerInterval = setInterval(() => {
        if (this.timer > 0) {
          this.timer--;
        } else {
          this.onTimeout();
        }
      }, 1000);
    },
    clearTimer() {
      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      }
    },
    onTimeout() {
      this.clearTimer();
      this.feedback = "Time's up!";
      this.revealSolution();
    },
    handleUserMove(moveSan) {
      if (!this.isQuizStarted || this.isRevealed) return;

      if (moveSan === this.currentPosition.expected_move_san) {
        this.clearTimer();
        this.feedback = "Correct!";
        this.completedCount++;
        this.isRevealed = true;
        this.$emit('correct-move');
      } else {
        this.feedback = `Not quite. Try again!`;
      }
    },
    revealSolution() {
      this.isRevealed = true;
      this.clearTimer();
    },
    nextPosition() {
      if (this.currentIdx < this.filteredPositions.length - 1) {
        this.currentIdx++;
        this.setupPosition();
      }
    },
    finishQuiz() {
      this.isQuizStarted = false;
      this.clearTimer();
      this.$emit('quiz-finished', {
        completed: this.completedCount,
        total: this.filteredPositions.length
      });
    }
  },
  beforeUnmount() {
    this.clearTimer();
  }
};
</script>

<style scoped>
.quiz-tab {
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  text-align: left;
}

.setup-group {
  margin-bottom: 15px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.radio-group {
  display: flex;
  gap: 15px;
}

.btn-start {
  background-color: #2196F3;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  width: 100%;
}

.btn-start:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.quiz-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  font-weight: bold;
}

.timer-low {
  color: #f44336;
}

.quiz-controls {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.btn-stop {
  background-color: #9e9e9e;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.btn-reveal {
  background-color: #ff9800;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.quiz-feedback {
  padding: 10px;
  border-radius: 4px;
  margin-top: 15px;
  text-align: center;
  font-weight: bold;
}

.feedback-info { background-color: #e3f2fd; color: #1976d2; }
.feedback-success { background-color: #e8f5e9; color: #2e7d32; }
.feedback-error { background-color: #ffebee; color: #c62828; }

.solution-box {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 4px;
  border-left: 4px solid #4caf50;
}

.solution-comment {
  margin-top: 10px;
  font-style: italic;
  font-size: 0.9em;
  color: #666;
}

.btn-next, .btn-finish {
  margin-top: 15px;
  background-color: #4caf50;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  width: 100%;
}

.no-positions {
  color: #888;
  font-style: italic;
}
</style>
