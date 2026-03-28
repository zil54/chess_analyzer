"""
Frontend Integration Guide for /analyze Endpoint

Examples showing how to call the Stockfish analysis from Vue.js frontend
"""

# ============================================================================
# EXAMPLE 1: Basic Analysis (JavaScript/Vue.js)
# ============================================================================

"""
// In your Vue component (e.g., FenControls.vue or Analyzer.vue)

async analyzePosition(fen) {
  try {
    const response = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        fen: fen,
        depth: 20,
        time_limit: 0.5
      })
    });

    if (!response.ok) {
      const error = await response.json();
      console.error('Analysis failed:', error);
      return null;
    }

    const evaluation = await response.json();
    console.log('✓ Analysis complete:', evaluation);
    
    return {
      bestMove: evaluation.best_move,
      score: evaluation.score_cp,  // in centipawns
      depth: evaluation.depth,
      pv: evaluation.pv,           // best continuation
      cached: evaluation.cached,   // was this cached?
      mate: evaluation.score_mate  // null unless mate
    };
  } catch (error) {
    console.error('Network error:', error);
    return null;
  }
}
"""

# ============================================================================
# EXAMPLE 2: Cache-Aware Analysis
# ============================================================================

"""
// Use cache information to show user feedback

async analyzeWithFeedback(fen) {
  const startTime = performance.now();
  
  const evaluation = await this.analyzePosition(fen);
  const elapsed = performance.now() - startTime;
  
  if (evaluation.cached) {
    console.log(`✓ Cached result (${elapsed.toFixed(0)}ms)`);
    this.showMessage('Using cached evaluation');
  } else {
    console.log(`✓ Computed result (${elapsed.toFixed(0)}ms)`);
    this.showMessage('Analyzed with Stockfish');
  }
  
  return evaluation;
}
"""

# ============================================================================
# EXAMPLE 3: Real-Time Analysis Display
# ============================================================================

"""
// In LiveAnalysisPanel.vue - Display evaluation as user navigates game

data() {
  return {
    evaluation: null,
    isAnalyzing: false,
    analysisSpeed: null  // 'cached' or 'computed'
  }
},

async handlePositionChange(fen) {
  this.isAnalyzing = true;
  
  try {
    const startTime = performance.now();
    
    const response = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fen: fen,
        depth: 25,          // Deeper analysis for display
        time_limit: 2.0     // More time for better evaluations
      })
    });
    
    if (response.ok) {
      const data = await response.json();
      const elapsed = performance.now() - startTime;
      
      this.evaluation = data;
      this.analysisSpeed = data.cached ? 'cached' : 'computed';
      
      // Update display
      console.log(
        `Evaluation: ${this.formatScore(data)} (${this.analysisSpeed}) ${elapsed.toFixed(0)}ms`
      );
    }
  } catch (error) {
    console.error('Analysis error:', error);
  } finally {
    this.isAnalyzing = false;
  }
},

formatScore(evaluation) {
  if (evaluation.score_mate !== null) {
    return `M${evaluation.score_mate}`;  // Mate in N
  }
  
  const score = evaluation.score_cp / 100;  // Convert to pawns
  return score >= 0 ? `+${score.toFixed(2)}` : score.toFixed(2);
}
"""

# ============================================================================
# EXAMPLE 4: Multiple Variations (Get multiple analysis lines)
# ============================================================================

"""
// For analysis panel showing best moves, second best, etc.
// Note: Current implementation returns single best line
// Future: Could extend to multipv=3 for top 3 moves

async analyzeMultiple(fen, numLines = 3) {
  // Currently /analyze returns only best line
  // This is a placeholder for future enhancement
  
  const analysis = await this.analyzePosition(fen);
  
  // Extract first 3 moves from PV as separate lines
  const pvMoves = analysis.pv.split(' ').slice(0, 3);
  
  return {
    mainLine: analysis,
    depth: analysis.depth,
    cached: analysis.cached
  };
}
"""

# ============================================================================
# EXAMPLE 5: Error Handling
# ============================================================================

"""
async analyzeWithErrorHandling(fen) {
  try {
    // Validate FEN on client side first
    if (!this.isValidFen(fen)) {
      throw new Error('Invalid FEN format');
    }
    
    const response = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fen: fen,
        depth: 20,
        time_limit: 0.5
      })
    });
    
    if (response.status === 400) {
      const error = await response.json();
      console.error('Bad request:', error.detail);
      this.showError('Invalid chess position');
      return null;
    }
    
    if (response.status === 503) {
      const error = await response.json();
      console.error('Service unavailable:', error.detail);
      this.showError('Database not configured');
      return null;
    }
    
    if (!response.ok) {
      console.error(`HTTP ${response.status}:`, await response.text());
      this.showError('Analysis failed');
      return null;
    }
    
    return await response.json();
    
  } catch (error) {
    console.error('Analysis error:', error);
    this.showError(error.message);
    return null;
  }
},

isValidFen(fen) {
  const fenRegex = /^([rnbqkpRNBQKP1-8]+\/){7}[rnbqkpRNBQKP1-8]+ [wb] (-|K?Q?k?q?) (-|[a-h][36]) \d+ \d+$/;
  return fenRegex.test(fen);
}
"""

# ============================================================================
# EXAMPLE 6: Caching Strategy (Smart re-analysis)
# ============================================================================

"""
// Only re-analyze when needed, use cached results otherwise

data() {
  return {
    analysisCache: new Map(),  // FEN -> evaluation
    currentFen: null,
    evaluation: null
  }
},

async analyzeSmartly(fen) {
  // Check local cache first (faster than DB)
  if (this.analysisCache.has(fen)) {
    console.log('✓ Using local cache');
    return this.analysisCache.get(fen);
  }
  
  // Check server cache (from database)
  const evaluation = await this.analyzePosition(fen);
  
  if (evaluation) {
    // Store in local cache for fast re-access
    this.analysisCache.set(fen, evaluation);
    return evaluation;
  }
  
  return null;
},

// Clear cache when needed
clearCache() {
  this.analysisCache.clear();
}
"""

# ============================================================================
# EXAMPLE 7: Depth Control (Trade quality for speed)
# ============================================================================

"""
// Different depths for different use cases

async analyzeQuick(fen) {
  // Fast check (low depth, short time)
  return this.analyzePosition(fen, {
    depth: 10,
    time_limit: 0.2
  });
},

async analyzeNormal(fen) {
  // Standard analysis (medium depth, medium time)
  return this.analyzePosition(fen, {
    depth: 20,
    time_limit: 0.5
  });
},

async analyzeDeep(fen) {
  // Deep analysis (high depth, long time)
  return this.analyzePosition(fen, {
    depth: 30,
    time_limit: 2.0
  });
},

async analyzePosition(fen, options = {}) {
  const {
    depth = 20,
    time_limit = 0.5,
    force_recompute = false
  } = options;
  
  const response = await fetch('http://localhost:8000/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fen,
      depth,
      time_limit,
      force_recompute
    })
  });
  
  if (response.ok) {
    return await response.json();
  }
  
  return null;
}
"""

# ============================================================================
# EXAMPLE 8: Game Analysis (Analyze all moves in PGN)
# ============================================================================

"""
// Analyze entire game by calling analyze for each position

async analyzeGamePositions(gamePositions) {
  const analyses = [];
  
  for (const position of gamePositions) {
    const analysis = await this.analyzePosition(position.fen);
    
    if (analysis) {
      analyses.push({
        ply: position.ply,
        fen: position.fen,
        san: position.san,
        evaluation: analysis
      });
    }
  }
  
  return analyses;
},

// Display evaluations alongside moves
displayGameAnalysis(analyses) {
  for (const analysis of analyses) {
    const score = this.formatScore(analysis.evaluation);
    const cached = analysis.evaluation.cached ? '(cached)' : '';
    
    console.log(
      `${analysis.ply}. ${analysis.san}: ${score} ${cached}`
    );
  }
}
"""

# ============================================================================
# EXAMPLE 9: Force Recompute (Update outdated analyses)
# ============================================================================

"""
// Re-analyze position at deeper depth

async deeperAnalysis(fen, newDepth = 30) {
  console.log(`Re-analyzing at depth ${newDepth}...`);
  
  const response = await fetch('http://localhost:8000/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fen: fen,
      depth: newDepth,
      time_limit: 2.0,
      force_recompute: true  // Bypass cache, always run Stockfish
    })
  });
  
  if (response.ok) {
    const evaluation = await response.json();
    console.log('✓ Deeper analysis complete:', evaluation);
    return evaluation;
  }
  
  return null;
}
"""

# ============================================================================
# EXAMPLE 10: Vue Component Template Integration
# ============================================================================

"""
<template>
  <div class="analysis-panel">
    <button @click="analyzeCurrentPosition">
      {{ isAnalyzing ? 'Analyzing...' : 'Analyze' }}
    </button>
    
    <div v-if="evaluation" class="evaluation">
      <p class="score">{{ formatScore(evaluation) }}</p>
      <p class="best-move">Best: {{ evaluation.best_move }}</p>
      <p class="pv">Line: {{ evaluation.pv }}</p>
      <p class="cached" v-if="evaluation.cached">
        ✓ From cache (instant)
      </p>
    </div>
    
    <div v-if="analysisError" class="error">
      {{ analysisError }}
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      evaluation: null,
      isAnalyzing: false,
      analysisError: null
    };
  },
  
  props: {
    fen: String
  },
  
  methods: {
    async analyzeCurrentPosition() {
      this.isAnalyzing = true;
      this.analysisError = null;
      
      try {
        const response = await fetch('http://localhost:8000/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fen: this.fen,
            depth: 20,
            time_limit: 0.5
          })
        });
        
        if (!response.ok) {
          throw new Error(`Analysis failed: ${response.status}`);
        }
        
        this.evaluation = await response.json();
        
      } catch (error) {
        this.analysisError = error.message;
        console.error(error);
        
      } finally {
        this.isAnalyzing = false;
      }
    },
    
    formatScore(eval) {
      if (eval.score_mate !== null) {
        return `Mate in ${eval.score_mate}`;
      }
      const score = (eval.score_cp / 100).toFixed(2);
      return score > 0 ? `+${score}` : score;
    }
  }
};
</script>

<style scoped>
.analysis-panel {
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.evaluation {
  margin-top: 1rem;
}

.score {
  font-size: 2em;
  font-weight: bold;
  color: #007bff;
}

.best-move {
  font-size: 1.2em;
  margin: 0.5rem 0;
}

.pv {
  font-family: monospace;
  color: #666;
}

.cached {
  color: green;
  font-size: 0.9em;
}

.error {
  color: red;
  padding: 0.5rem;
  background-color: #ffe6e6;
  border-radius: 4px;
}
</style>
"""

print("=== Frontend Integration Examples ===")
print("See comments above for 10 complete integration examples")
print("\nQuick Start:")
print("1. Use Example 1 for basic analysis")
print("2. Use Example 5 for proper error handling")
print("3. Use Example 10 for complete Vue component")

