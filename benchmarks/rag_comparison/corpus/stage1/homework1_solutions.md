# CS 301 — Homework 1: Solutions

**Author:** Alex Kim
**Course:** CS 301 Advanced Machine Learning, Prof. Sarah Chen
**Due:** February 6, 2026

---

## Problem 1: Backpropagation Through a Two-Layer Network (25 pts)

Consider a two-layer fully connected network with ReLU activation:

    h = ReLU(W₁x + b₁)
    ŷ = W₂h + b₂

The loss is L = ½‖ŷ − y‖².

### Part (a): Derive the gradients

Using the chain rule:

    ∂L/∂b₂ = ŷ − y
    ∂L/∂W₂ = (ŷ − y) hᵀ
    ∂L/∂h  = W₂ᵀ (ŷ − y)
    ∂L/∂b₁ = diag(ReLU'(W₁x + b₁)) · W₂ᵀ (ŷ − y)
    ∂L/∂W₁ = [diag(ReLU'(W₁x + b₁)) · W₂ᵀ (ŷ − y)] xᵀ

where ReLU'(z) = 1 if z > 0 and 0 otherwise.

### Part (b): Implement in NumPy (10 pts)

```python
import numpy as np

def forward(x, W1, b1, W2, b2):
    z1 = W1 @ x + b1
    h = np.maximum(0, z1)        # ReLU
    y_hat = W2 @ h + b2
    return z1, h, y_hat

def backward(x, y, z1, h, y_hat, W2):
    m = x.shape[1]
    dy = (y_hat - y) / m
    dW2 = dy @ h.T
    db2 = np.sum(dy, axis=1, keepdims=True)
    dh = W2.T @ dy
    dz1 = dh * (z1 > 0).astype(float)  # ReLU gradient
    dW1 = dz1 @ x.T
    db1 = np.sum(dz1, axis=1, keepdims=True)
    return dW1, db1, dW2, db2
```

---

## Problem 2: Transformer Attention Complexity (25 pts)

### Part (a): Computational complexity

Given a sequence of length *n* and embedding dimension *d*, standard scaled dot-product attention computes:

    Q = XW_Q,  K = XW_K,  V = XW_V      — each O(n·d²)
    Scores = QKᵀ / √d                     — O(n²·d)
    Attn = softmax(Scores) V               — O(n²·d)

**Total: O(n²·d)**, dominated by the *n²* attention score computation when *n > d*.

### Part (b): Memory complexity

The attention matrix (n × n) requires **O(n²)** space. For n = 8192 and float32, that is approximately 256 MB — prohibitive for very long sequences.

### Part (c): Sparsity

Prof. Chen's ASA framework reduces effective complexity to O(n·k·d) where k ≪ n is the average number of attended positions per query. This is a key topic we will explore later in the semester.

---

## Problem 3: SGD Convergence (25 pts)

### Part (a): Learning rate decay

For convex objectives with Lipschitz-continuous gradients (constant L), choosing η_t = 1/(Lt) gives:

    E[f(x_T)] − f(x*) ≤ ‖x₁ − x*‖² · L / (2T)

which converges at rate O(1/T).

### Part (b): Mini-batch SGD

With batch size b, the variance of the stochastic gradient estimate decreases as O(1/b), trading off per-iteration cost for variance reduction. An optimal batch size balances gradient computation cost against convergence speed.

---

## Problem 4: Conceptual Questions (25 pts)

### Part (a): Why does batch normalization help training?

Batch normalization standardizes activations within each mini-batch, reducing **internal covariate shift**. This allows higher learning rates, acts as a mild regularizer, and smooths the loss landscape.

### Part (b): Residual connections

Skip connections in ResNets mitigate the **vanishing gradient** problem in deep networks. They create a direct path for gradient flow, enabling training of networks with hundreds of layers.

---

*References: Goodfellow et al., Deep Learning, Chapters 6–8; Vaswani et al., "Attention Is All You Need," NeurIPS 2017.*
