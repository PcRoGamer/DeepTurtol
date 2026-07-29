# CS 490: Advanced Topics Seminar — Notes

**Instructor:** Prof. Sarah Chen
**Topic:** Scaling Laws and Emergent Abilities in Large Language Models
**Date:** April 22, 2026

---

## Overview

This seminar session explored the empirical and theoretical foundations of scaling laws in neural language models, and the controversial concept of emergent abilities.

## 1. Kaplan et al. (2020) Scaling Laws

OpenAI's landmark paper established power-law relationships:

    L(N) ∝ N^(−α_N)     (model parameters)
    L(D) ∝ D^(−α_D)     (training data)
    L(C) ∝ C^(−α_C)     (compute budget)

where L is the cross-validation loss. Typical exponents: α_N ≈ 0.076, α_D ≈ 0.095, α_C ≈ 0.050.

**Key insight:** Performance improves predictably with scale, and the optimal allocation of compute between model size and data size follows a specific ratio.

## 2. Chinchilla Scaling (Hoffmann et al., 2022)

The Chinchilla paper challenged the "bigger model" approach by showing that for a given compute budget, the optimal model size scales linearly with the number of training tokens:

    N_opt ∝ C^(0.5),  D_opt ∝ C^(0.5)

This implies many large models (including GPT-3) were **undertrained** relative to their size. The 70B Chinchilla model outperformed the 175B Gopher despite being 2.5× smaller.

## 3. Emergent Abilities

**Wei et al. (2022)** defined emergent abilities as capabilities that are:

> "absent in small models but present in large models"

Examples include:
- **Chain-of-thought reasoning:** Models can solve multi-step problems when prompted to "think step by step," but only above ~100B parameters.
- **Few-shot learning:** Large models can learn new tasks from examples in the context window — this connects directly to Prof. Chen's research on few-shot learning (see prof_chen_research.md).
- **Code generation:** Ability to write executable code appears suddenly at sufficient scale.

### Criticism

**Schaeffer et al. (2023)** argued that emergent abilities are **artifacts of metric choice**. Using smooth metrics (e.g., Brier score instead of exact-match accuracy), performance improves gradually. The "emergence" disappears when we measure correctly.

## 4. Discussion

### Alex Kim's Presentation: ASA and Scaling

Alex Kim (Ph.D. student in Prof. Chen's lab) presented preliminary results on how the ASA (Adaptive Sparse Attention) mechanism scales with model size:

- At small model sizes (< 1B params), ASA provides modest gains (2–3% on perplexity).
- At larger sizes (7B+), ASA shows more significant improvements (5–7%), suggesting that **sparsity becomes more valuable as models grow**.
- Alex hypothesizes that larger models have more redundant attention patterns that ASA can prune.

### Questions for Further Reading

1. Does ASA interact with Chinchilla-optimal training? Can sparse models be trained with less data?
2. Are "few-shot learning" abilities truly emergent, or do they improve gradually with scale?
3. How do scaling laws apply to multimodal models (vision + language)?

## Attendees

Prof. Sarah Chen, Alex Kim, Priya Sharma, Marcus Johnson, Fatima Al-Rashid, Derek Lee, and 8 other graduate students.

## References

- Kaplan, J. et al. "Scaling Laws for Neural Language Models." *arXiv:2001.08361*, 2020.
- Hoffmann, J. et al. "Training Compute-Optimal Large Language Models." *NeurIPS*, 2022.
- Wei, J. et al. "Emergent Abilities of Large Language Models." *TMLR*, 2022.
- Schaeffer, R. et al. "Are Emergent Abilities of LLMs a Mirage?" *NeurIPS*, 2023.
