<template>
  <div class="nag-palette-wrapper" @mouseenter="isHovered = true" @mouseleave="isHovered = false">
    <div class="palette-header">
      <span class="palette-icon">✎</span>
      <span class="palette-label">Edit Move</span>
    </div>

    <div class="nag-palette" v-show="isHovered">
      <div class="palette-title">Annotations</div>
      <div class="palette-grid">
        <!-- Move Quality -->
        <div class="palette-category">
          <div class="category-label">Quality</div>
          <div class="category-buttons">
            <button
              @click="addNag(1)"
              title="Good move"
              class="nag-btn"
              :class="{ active: hasNag(1) }"
            >
              !
            </button>
            <button
              @click="addNag(2)"
              title="Bad move"
              class="nag-btn"
              :class="{ active: hasNag(2) }"
            >
              ?
            </button>
            <button
              @click="addNag(3)"
              title="Excellent move"
              class="nag-btn"
              :class="{ active: hasNag(3) }"
            >
              !!
            </button>
            <button
              @click="addNag(4)"
              title="Blunder"
              class="nag-btn"
              :class="{ active: hasNag(4) }"
            >
              ??
            </button>
            <button
              @click="addNag(5)"
              title="Interesting move"
              class="nag-btn"
              :class="{ active: hasNag(5) }"
            >
              !?
            </button>
            <button
              @click="addNag(6)"
              title="Dubious move"
              class="nag-btn"
              :class="{ active: hasNag(6) }"
            >
              ?!
            </button>
          </div>
        </div>

        <!-- Position Assessment -->
        <div class="palette-category">
          <div class="category-label">Position</div>
          <div class="category-buttons">
            <button
              @click="addNag(10)"
              title="Equal position"
              class="nag-btn"
              :class="{ active: hasNag(10) }"
            >
              =
            </button>
            <button
              @click="addNag(14)"
              title="Slightly better for White"
              class="nag-btn"
              :class="{ active: hasNag(14) }"
            >
              +=
            </button>
            <button
              @click="addNag(15)"
              title="Slightly better for Black"
              class="nag-btn"
              :class="{ active: hasNag(15) }"
            >
              =+
            </button>
            <button
              @click="addNag(16)"
              title="Better for White"
              class="nag-btn"
              :class="{ active: hasNag(16) }"
            >
              +/-
            </button>
            <button
              @click="addNag(17)"
              title="Better for Black"
              class="nag-btn"
              :class="{ active: hasNag(17) }"
            >
              -/+
            </button>
            <button
              @click="addNag(18)"
              title="Winning for White"
              class="nag-btn"
              :class="{ active: hasNag(18) }"
            >
              +-
            </button>
            <button
              @click="addNag(19)"
              title="Winning for Black"
              class="nag-btn"
              :class="{ active: hasNag(19) }"
            >
              -+
            </button>
          </div>
        </div>

        <!-- Mixed Evaluations -->
        <div class="palette-category">
          <div class="category-label">Mixed</div>
          <div class="category-buttons">
            <button
              @click="addNag(22)"
              title="Advantage over Disadvantage"
              class="nag-btn nag-vertical"
              :class="{ active: hasNag(22) }"
            >
              <span>+</span><span>−</span>
            </button>
            <button
              @click="addNag(23)"
              title="Disadvantage over Advantage"
              class="nag-btn nag-vertical"
              :class="{ active: hasNag(23) }"
            >
              <span>−</span><span>+</span>
            </button>
            <button
              @click="addNag(131)"
              title="White has compensation for material"
              class="nag-btn nag-vertical"
              :class="{ active: hasNag(131) }"
            >
              <span>+</span><span>=</span>
            </button>
            <button
              @click="addNag(133)"
              title="Black compensation for material"
              class="nag-btn nag-vertical"
              :class="{ active: hasNag(133) }"
            >
              <span>=</span><span>+</span>
            </button>
          </div>
        </div>

        <!-- Special -->
        <div class="palette-category">
          <div class="category-label">Special</div>
          <div class="category-buttons">
            <button
              @click="addNag(12)"
              title="Unclear position"
              class="nag-btn"
              :class="{ active: hasNag(12) }"
            >
              ∞
            </button>
            <button
              @click="addNag(130)"
              title="Zugzwang"
              class="nag-btn"
              :class="{ active: hasNag(130) }"
            >
              Z
            </button>
            <button
              @click="addNag(138)"
              title="White has counterplay"
              class="nag-btn"
              :class="{ active: hasNag(138) }"
            >
              ⇄
            </button>
            <button
              @click="addNag(32)"
              title="Repetition"
              class="nag-btn"
              :class="{ active: hasNag(32) }"
            >
              ⟳
            </button>
            <button
              @click="addNag(36)"
              title="Initiative"
              class="nag-btn"
              :class="{ active: hasNag(36) }"
            >
              ↑
            </button>
            <button
              @click="addNag(40)"
              title="Attack"
              class="nag-btn"
              :class="{ active: hasNag(40) }"
            >
              →
            </button>
          </div>
        </div>

        <!-- Clear -->
        <div class="palette-category">
          <div class="category-buttons">
            <button
              @click="clearNags"
              class="nag-btn nag-clear"
              title="Clear all annotations"
            >
              Clear
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NagPalette',
  props: {
    currentNode: {
      type: Object,
      default: null
    }
  },
  emits: ['update-nags'],
  data() {
    return {
      selectedNags: new Set(),
      isHovered: false
    };
  },
  watch: {
    currentNode: {
      handler(newNode) {
        if (newNode) {
          this.selectedNags = new Set(newNode.nags || []);
        } else {
          this.selectedNags.clear();
        }
      },
      immediate: true,
      deep: true
    }
  },
  methods: {
    hasNag(nag) {
      return this.selectedNags.has(nag);
    },
    addNag(nag) {
      if (this.selectedNags.has(nag)) {
        this.selectedNags.delete(nag);
      } else {
        this.selectedNags.add(nag);
      }
      this.$emit('update-nags', Array.from(this.selectedNags));
    },
    clearNags() {
      this.selectedNags.clear();
      this.$emit('update-nags', []);
    }
  }
};
</script>

<style scoped>
.nag-palette-wrapper {
  position: relative;
  display: inline-block;
}

.palette-header {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background-color: #f0f7ff;
  border: 1px solid #2196F3;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  color: #1976D2;
  transition: all 0.2s ease;
}

.palette-header:hover {
  background-color: #e3f2fd;
  border-color: #1976D2;
}

.palette-icon {
  font-size: 1rem;
}

.palette-label {
  letter-spacing: 0.3px;
}

.nag-palette {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 8px;
  min-width: 380px;
  max-width: 450px;
  padding: 12px;
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
}

.palette-title {
  font-weight: 600;
  font-size: 0.9rem;
  color: #2c3e50;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e0e0e0;
}

.palette-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.palette-category {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.category-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.category-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(40px, 1fr));
  gap: 4px;
}

.nag-btn {
  padding: 6px 4px;
  font-weight: 600;
  font-size: 0.85rem;
  background-color: #fff;
  border: 1px solid #d0d0d0;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #2c3e50;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
}

.nag-btn.nag-vertical {
  display: flex;
  flex-direction: column;
  font-size: 0.7rem;
  line-height: 0.9;
  padding: 4px 2px;
}

.nag-btn.nag-vertical span {
  display: block;
}

.nag-btn:hover {
  background-color: #e8f4f8;
  border-color: #2196F3;
  color: #1976D2;
}

.nag-btn.active {
  background-color: #2196F3;
  color: white;
  border-color: #1976D2;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.4);
}

.nag-clear {
  background-color: #f5f5f5;
  color: #d32f2f;
  border-color: #d32f2f;
  font-weight: 600;
  grid-column: 1 / -1;
}

.nag-clear:hover {
  background-color: #ffebee;
}
</style>




