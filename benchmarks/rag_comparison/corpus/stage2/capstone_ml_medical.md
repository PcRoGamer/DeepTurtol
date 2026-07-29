# CS 301 Capstone Project: Few-Shot Medical Image Classification

**Title:** Prototypical Networks with Cross-Attention for Few-Shot Dermoscopy Classification
**Authors:** Priya Sharma and Marcus Johnson
**Advisor:** Prof. Sarah Chen
**External Collaborator:** Dr. Emily Watson, Department of Biomedical Engineering
**Course:** CS 301 Advanced Machine Learning, Spring 2026

---

## Abstract

We present a few-shot learning system for classifying rare skin conditions from dermoscopy images. Using Prototypical Networks enhanced with cross-attention between support and query embeddings, our model achieves **73.5% accuracy in the 5-shot setting** across 15 dermatological conditions, significantly outperforming the baseline Prototypical Network (68.2%) and matching-network (65.7%) approaches.

## 1. Introduction

Rare skin conditions present a significant diagnostic challenge: dermatologists may encounter fewer than 10 cases of a specific disease during their entire career. Deep learning models typically require hundreds or thousands of labeled examples per class, making them poorly suited to rare-condition diagnosis.

Few-shot learning addresses this by training models to generalize from very few examples. In collaboration with Dr. Emily Watson's biomedical engineering group, we curated a dataset of **1,200 dermoscopy images** spanning **15 dermatological conditions**, with per-class counts as low as 20 images.

## 2. Related Work

- **Prototypical Networks** (Snell et al., 2017): Learn a metric space where classification is performed by computing distances to class prototypes (mean embeddings).
- **Matching Networks** (Vinyals et al., 2016): Use attention-based matching with episodic training.
- **MAML** (Finn et al., 2017): Model-agnostic meta-learning that finds initialization parameters.
- **Prof. Chen's ASA Framework:** Adaptive Sparse Attention reduces quadratic attention complexity and has been shown to improve feature extraction in low-data regimes (see prof_chen_research.md).

## 3. Method

Our architecture builds on Prototypical Networks with two key modifications:

1. **Cross-attention refinement:** After computing initial prototypes as mean support embeddings, we apply a cross-attention layer where each support embedding attends to all other support embeddings within the same class. This allows prototypes to incorporate relational information between examples.

2. **Sparse attention regularization:** Inspired by Prof. Chen's ASA work, we apply a sparsity mask to the cross-attention weights, encouraging the model to focus on the most informative support-query relationships. This reduces overfitting in the few-shot regime.

### Architecture

    Input images → ResNet-18 encoder → Embedding (64-d)
    → Cross-attention refinement (within-class)
    → Prototypes (15 × 64)
    → Distance-based classification

## 4. Experiments and Results

| Method | 1-shot | 5-shot | 10-shot |
|--------|--------|--------|---------|
| Matching Network | 52.1% | 65.7% | 71.3% |
| ProtoNet (baseline) | 55.8% | 68.2% | 74.0% |
| MAML | 53.4% | 66.9% | 72.5% |
| **ProtoNet + CrossAttn (Ours)** | **58.3%** | **73.5%** | **77.8%** |

Our best model achieves **73.5% 5-shot accuracy**, a 5.3 percentage point improvement over the standard Prototypical Network.

## 5. Ablation Study

- Removing cross-attention: accuracy drops to 68.2% (baseline).
- Removing ASA-inspired sparsity: accuracy drops to 71.1%, suggesting regularization is important.
- Using full attention (no sparsity): accuracy is 71.9%, with significantly higher memory usage.

## 6. Discussion

The cross-attention mechanism allows prototypes to capture within-class variation — for instance, different presentations of the same skin condition. The sparsity constraint prevents the model from memorizing spurious correlations in the small support sets.

**Limitations:** The dataset is relatively small and single-institution. Future work should include multi-center validation and integration with Dr. Watson's clinical decision support pipeline.

## 7. Acknowledgments

We thank Prof. Chen for her guidance and for sharing insights from the ASA framework. We are grateful to Dr. Emily Watson for access to the dermoscopy dataset and clinical expertise. Alex Kim provided valuable feedback on the attention implementation.

---

*See also: biomedical_ml_collab.md for the broader collaboration context; hw3_transformers.md for related coursework.*
