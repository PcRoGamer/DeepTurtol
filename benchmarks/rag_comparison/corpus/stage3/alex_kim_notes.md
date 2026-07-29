# Alex Kim — Research Notes: Sparse Attention Experiments

**Ph.D. Student, Prof. Sarah Chen's Lab**
**Period:** January – April 2026

---

## Week 1 (Jan 12–16): Setup

Set up the experimental environment for ASA (Adaptive Sparse Attention) experiments:
- PyTorch 2.2 with CUDA 12.1
- Custom ASA implementation based on Chen et al. (2022)
- Baseline: standard multi-head attention (8 heads, d_model=256)
- Dataset: synthetic sequence classification (length 512, 10 classes)

**Initial results:** ASA with k=64 achieves 94.2% accuracy vs. 95.1% full attention. Only 23% of attention weight computed.

## Week 2 (Jan 19–23): Gating Network Design

Experimented with different gating architectures for ASA:
- Linear gate: 93.8% (too simple)
- 2-layer MLP: 94.2%
- **Residual gate with layer norm: 94.7%** ← selected for further experiments

The residual gate allows the model to learn a perturbation on top of uniform attention, which converges faster.

## Week 3 (Jan 26–30): Sparsity Analysis

Analyzed what ASA learns to attend to in a simple language model:
- Adjacent tokens: 45% of attention budget
- Sentence-level tokens (first word of each sentence): 20%
- Task-relevant tokens (e.g., negation words for sentiment): 35%

This suggests ASA is learning linguistically meaningful sparsity patterns, not just local neighborhoods.

## Week 4 (Feb 2–6): Dermoscopy Dataset

Received the dermoscopy dataset from Dr. Emily Watson (1,200 images, 15 conditions). Preprocessing:
- Resize to 224×224
- Normalize with ImageNet statistics
- Augmentation: random horizontal flip, color jitter

Split: 60% train (episodic), 20% val, 20% test. Each episode samples C classes from N-way task.

## Week 5 (Feb 9–13): ProtoNet Baseline

Implemented Prototypical Networks baseline on dermoscopy:
- Backbone: ResNet-18 (pretrained on ImageNet)
- Embedding dim: 64
- Results: 55.8% (1-shot), 68.2% (5-shot), 74.0% (10-shot)

These match reported numbers in the literature.

## Week 6 (Feb 16–20): Cross-Attention Prototype Refinement

Implemented cross-attention between support embeddings within each class:
- Support embeddings attend to each other before averaging into prototypes.
- Without sparsity: 71.9% (5-shot) — improved but overfits.
- With ASA sparsity (k=8): **73.5% (5-shot)** ← significant improvement.

The sparsity prevents overfitting in the cross-attention by limiting each support embedding to attending to at most 8 others (out of ~40 support examples in 5-shot 8-way).

## Week 7 (Feb 23–27): Ablation Studies

| Configuration | 5-shot acc. |
|---|---|
| ProtoNet baseline | 68.2% |
| + cross-attention | 71.9% |
| + ASA sparsity (k=8) | 73.5% |
| + ASA sparsity (k=4) | 71.1% |
| + ASA sparsity (k=16) | 73.2% |

Sweet spot is k=8 for this dataset. Lower k under-attends, higher k re-introduces overfitting.

## Week 8 (Mar 2–6): Collaboration with Marcus

Marcus Johnson joined the project to handle the medical image processing pipeline:
- Implemented test-time augmentation (TTA): horizontal flip + color jitter
- TTA improves 5-shot accuracy from 73.5% to 74.2%
- Marcus is writing the capstone report (see capstone_ml_medical.md)

## Week 9 (Mar 9–13): Scaling Experiments

Tested ASA on larger models:
- ResNet-50 backbone: 75.1% (5-shot), up from 73.5% with ResNet-18
- ViT-Small backbone: 76.8% (5-shot) — best result so far

ViT's patch-based attention interacts well with the ASA sparsity pattern.

## Week 10 (Mar 16–20): Paper Preparation

Started writing MICCAI paper with Priya Sharma (see biomedical_ml_collab.md):
- Paper 1: "Sparse Attention for Few-Shot Medical Image Classification"
- Target: MICCAI 2027
- Drafting introduction and related work sections.

## Week 11 (Mar 23–27): Seminar Presentation

Presented ASA scaling results at CS 490 seminar (see cs490_seminar_notes.md):
- ASA provides increasing gains as model size grows
- At 1B parameters, ASA saves 40% compute with <1% quality loss
- Prof. Chen suggested exploring ASA for the music generation project too

## Week 12 (Apr 6–10): Integration with Music Generation

Brief consultation with Fatima Al-Rashid and Derek Lee on their music generation project (see project_gan_music.md):
- Shared the gating network architecture from ASA
- Their results validate that sparsity helps even in generative settings

## Summary

Key results from this research period:
1. ASA gating network with residual connections achieves 94.7% on synthetic tasks.
2. ProtoNet + cross-attention + ASA sparsity achieves **73.5% 5-shot accuracy** on dermoscopy.
3. ASA gains increase with model scale (confirmed at seminar).
4. Two papers in preparation: MICCAI 2027 and Scientific Data.
