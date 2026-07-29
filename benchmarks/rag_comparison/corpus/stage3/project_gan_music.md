# CS 301 Project: Attention-Based Music Generation

**Title:** Sparse Attention for Efficient Neural Music Composition
**Authors:** Fatima Al-Rashid and Derek Lee
**Course:** CS 301 Advanced Machine Learning, Prof. Sarah Chen
**Date:** April 2026

---

## Abstract

We present an attention-based music generation system that leverages Prof. Chen's Adaptive Sparse Attention (ASA) mechanism to reduce parameter count while maintaining generation quality. Our model uses **39% fewer parameters** than a comparable full-attention transformer while achieving comparable music quality scores as evaluated by human listeners and automated metrics.

## 1. Introduction

Neural music generation has advanced rapidly with transformer-based models. However, the quadratic complexity of self-attention limits the sequence lengths that can be modeled — a critical limitation for music, where long-range structure (themes, key changes, repetition) is essential.

We propose using **sparse attention patterns** to model long musical sequences efficiently. Our approach is inspired by Prof. Chen's ASA framework (see prof_chen_research.md), which demonstrates that not all token-to-token relationships are necessary for high-quality generation.

## 2. Related Work

- **Music Transformer** (Huang et al., 2018): Applied self-attention to symbolic music generation, using relative attention for pitch and time.
- **ASA** (Chen et al., 2022): Adaptive Sparse Attention for efficient transformers.
- **Performer** (Choromanski et al., 2021): Linear attention via random feature approximation.

## 3. Model Architecture

### Input Representation

We represent music as a sequence of events: (pitch, duration, velocity, time_shift). The vocabulary size is 512, and sequences are up to 4096 tokens long.

### Sparse Attention Design

We implement three attention configurations:

1. **Full attention** (baseline): Standard O(n²d) attention.
2. **Local + Global:** 90% local sliding window (w=128) + 10% global tokens that attend to everything. Cost: O(n·w·d + g²·d) where g = 0.1n.
3. **ASA-inspired:** Learned sparsity with top-k selection (k=64). The gating network learns to identify which key positions are most relevant for each query.

### Training

- **Dataset:** MAESTRO dataset (22 hours of piano performances).
- **Loss:** Cross-entropy on next-token prediction.
- **Optimizer:** AdamW with cosine learning rate schedule.
- **Training:** 500K steps, batch size 16, sequence length 2048.

## 4. Results

| Model | Params | FLOPs | Melody Coherence | Human Pref. |
|-------|--------|-------|------------------|-------------|
| Full Attention | 142M | 1.0× | 0.84 | 34% |
| Local + Global | 108M (−24%) | 0.71× | 0.82 | 28% |
| **ASA-Inspired** | **87M (−39%)** | **0.52×** | **0.83** | **38%** |

Surprisingly, the ASA-inspired model received the **highest human preference rating** (38%), suggesting that sparse attention may act as a useful inductive bias that encourages the model to focus on musically meaningful relationships.

### Analysis of Learned Sparsity Patterns

Visualization of the learned sparsity patterns (using techniques from Prof. Rodriguez's research on low-rank matrix approximation, see rodriguez_research.md) reveals that:
- The model strongly attends to the **previous occurrence of similar motifs** (repetition tracking).
- **Harmonic relationships** (intervals of octaves, fifths, and thirds) create long-range attention patterns.
- **Rhythmic patterns** at regular intervals create periodic attention structures.

## 5. Ablation Study

| k (top-k) | Params | Melody Coherence |
|-----------|--------|------------------|
| 32 | 72M | 0.78 |
| 64 | 87M | 0.83 |
| 128 | 108M | 0.84 |
| 256 | 128M | 0.85 |

The sweet spot is k=64, achieving near-full-attention quality with 39% fewer parameters.

## 6. Conclusions

Sparse attention is effective for music generation. The ASA-inspired approach not only reduces computational cost but may improve generation quality by filtering out irrelevant token relationships. Future work includes extending to multi-instrument generation and integrating Prof. Rodriguez's randomized SVD for further efficiency gains.

---

*Code available at: github.com/cs301-music-gen/sparse-music*
