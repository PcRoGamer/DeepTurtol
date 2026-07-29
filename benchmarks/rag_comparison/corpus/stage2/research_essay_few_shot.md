# Literature Review: Meta-Learning for Few-Shot Classification

**Author:** Priya Sharma
**Course:** CS 301 Advanced Machine Learning, Prof. Sarah Chen
**Date:** March 2026

---

## 1. Introduction

Few-shot learning aims to classify new objects from very few labeled examples — a single image (1-shot) or a handful (5-shot). This capability is critical in domains where data is scarce: rare disease diagnosis, robotics, and personalized recommendation.

This review surveys the major approaches to few-shot classification, with emphasis on metric-based, optimization-based, and attention-based methods.

## 2. Metric-Based Approaches

### 2.1 Siamese Networks (Koch et al., 2015)

The earliest deep learning approach to few-shot classification used **Siamese networks** — twin networks sharing weights that learn a similarity function. Two inputs are passed through the same network, and a distance metric determines if they belong to the same class. Limitation: the network is trained for verification (same/different) rather than classification, requiring a separate procedure for k-way tasks.

### 2.2 Matching Networks (Vinyals et al., 2016)

Matching Networks introduced **episodic training**: the model is trained on tasks that mimic the test-time few-shot scenario. Each episode consists of a support set S = {(xᵢ, yᵢ)} and a query point. The prediction uses a weighted nearest-neighbor with attention:

    P(ŷ|q, S) = Σᵢ a(q, xᵢ) · yᵢ

where a(q, xᵢ) = softmax(f(q)ᵀ g(xᵢ)) is a learned attention kernel.

### 2.3 Prototypical Networks (Snell et al., 2017)

Prototypical Networks (ProtoNets) simplify matching networks by computing a **prototype** for each class as the mean of its support embeddings:

    cₖ = (1/|Sₖ|) Σ_{(x,y)∈Sₖ} f(x)

Classification is performed by nearest neighbor in embedding space. ProtoNets are computationally efficient and remarkably effective. Our capstone project (see capstone_ml_medical.md) builds directly on this framework.

## 3. Optimization-Based Approaches

### 3.1 MAML (Finn et al., 2017)

Model-Agnostic Meta-Learning (MAML) learns an **initialization** of model parameters from which a few gradient steps on a small support set will yield good performance. The outer loop optimizes:

    θ* = θ − β ∇_θ Σ_{task_i} L_{task_i}(θ − α ∇_θ L_{task_i}(θ))

MAML is elegant but expensive: computing second-order gradients requires O(n²) memory.

### 3.2 Reptile (Nichol et al., 2018)

Reptile simplifies MAML by avoiding second-order gradients entirely. It runs SGD on each task and moves the initialization toward the task-specific solution. Surprisingly competitive with MAML at a fraction of the computational cost.

## 4. Attention and Transformer Approaches

Recent work has applied transformer architectures to few-shot learning:

- **FEAT** (Ye et al., 2020): Uses transformer layers to refine class prototypes via self-attention across support examples.
- **Prof. Chen's ASA Framework** (Chen et al., 2022): Adaptive Sparse Attention has shown promise in few-shot settings by dynamically selecting the most relevant support-query relationships, reducing noise from irrelevant examples.

The connection to our capstone work: we adapted ASA-inspired sparsity into the Prototypical Network's cross-attention layer, achieving our best results (73.5% 5-shot accuracy on the dermoscopy dataset).

## 5. Comparative Analysis

| Method | Type | Strengths | Weaknesses |
|--------|------|-----------|------------|
| Siamese Nets | Metric | Simple | Not episodic |
| Matching Nets | Metric | Episodic | Complex attention |
| ProtoNets | Metric | Efficient, effective | Ignores within-class variation |
| MAML | Optimization | Flexible | Computationally expensive |
| Transformer/ASA | Attention | Captures relations | Requires careful regularization |

## 6. Conclusion

Few-shot learning has matured rapidly. The most effective current approaches combine metric learning with attention mechanisms. Future directions include cross-modal few-shot learning, continual few-shot learning, and clinical deployment (see biomedical_ml_collab.md).

## References

1. Koch, G. et al. "Siamese Neural Networks for One-Shot Image Recognition." *ICML Deep Learning Workshop*, 2015.
2. Vinyals, O. et al. "Matching Networks for One Shot Learning." *NeurIPS*, 2016.
3. Snell, J. et al. "Prototypical Networks for Few-shot Learning." *NeurIPS*, 2017.
4. Finn, C. et al. "Model-Agnostic Meta-Learning for Fast Adaptation of Deep Networks." *ICML*, 2017.
5. Nichol, A. et al. "Reptile: A Scalable Metalearning Algorithm." *arXiv*, 2018.
6. Ye, M. et al. "FEAT: Few-Shot Embedding Adaptation with Transformers." *ICML*, 2020.
7. Chen, S. et al. "Adaptive Sparse Attention for Scalable Transformers." *NeurIPS*, 2022.
