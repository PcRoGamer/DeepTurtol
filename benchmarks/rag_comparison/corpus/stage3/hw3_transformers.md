# CS 301 — Homework 3: Transformers and Attention

**Author:** Marcus Johnson
**Course:** CS 301 Advanced Machine Learning, Prof. Sarah Chen
**Due:** April 10, 2026

---

## Problem 1: Multi-Head Attention Implementation (30 pts)

### Part (a): Scaled Dot-Product Attention (10 pts)

Implement the scaled dot-product attention function:

```python
import torch
import torch.nn.functional as F
import math

def scaled_dot_product_attention(Q, K, V, mask=None):
    # Args:
    #   Q: (batch, heads, seq_len, d_k)
    #   K: (batch, heads, seq_len, d_k)
    #   V: (batch, heads, seq_len, d_v)
    #   mask: optional (batch, 1, 1, seq_len) or (batch, 1, seq_len, seq_len)
    # Returns:
    #   output: (batch, heads, seq_len, d_v)
    #   attention_weights: (batch, heads, seq_len, seq_len)
    d_k = Q.size(-1)
    scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(mask == 0, float('-inf'))
    attention_weights = F.softmax(scores, dim=-1)
    output = torch.matmul(attention_weights, V)
    return output, attention_weights
```

### Part (b): Multi-Head Attention (10 pts)

```python
class MultiHeadAttention(torch.nn.Module):
    def __init__(self, d_model, num_heads):
        super().__init__()
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        self.W_Q = torch.nn.Linear(d_model, d_model)
        self.W_K = torch.nn.Linear(d_model, d_model)
        self.W_V = torch.nn.Linear(d_model, d_model)
        self.W_O = torch.nn.Linear(d_model, d_model)

    def forward(self, Q, K, V, mask=None):
        batch_size = Q.size(0)
        Q = self.W_Q(Q).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        K = self.W_K(K).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        V = self.W_V(V).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        attn_output, attn_weights = scaled_dot_product_attention(Q, K, V, mask)
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        return self.W_O(attn_output), attn_weights
```

### Part (c): Complexity analysis (10 pts)

With sequence length n, embedding dimension d, and h heads:
- Each head operates on dimension d_k = d/h.
- Per-head cost: O(n² · d/h).
- Total across h heads: O(n² · d) — same as single-head, but with **representational power** of h independent attention patterns.

## Problem 2: Sparse Attention Patterns (35 pts)

### Part (a): Prof. Chen's ASA Framework (15 pts)

The Adaptive Sparse Attention (ASA) mechanism (see prof_chen_research.md) reduces attention complexity by selecting a subset of key positions for each query. Specifically:

1. A **gating network** g(qᵢ) produces a sparse distribution over keys.
2. Only the top-k keys (k ≪ n) are attended to.
3. The effective complexity becomes O(n · k · d) instead of O(n² · d).

**Advantages:**
- Reduces memory from O(n²) to O(n·k).
- Can learn task-specific sparsity patterns.
- Particularly effective for sequences with local structure (e.g., text, time series).

**Disadvantages:**
- Requires careful tuning of sparsity level k.
- May miss long-range dependencies if k is too small.
- Training the gating network adds complexity.

### Part (b): Fixed sparse patterns (10 pts)

Compare three fixed sparse attention patterns:
1. **Local (sliding window):** Each position attends to w neighbors. Cost: O(n·w·d).
2. **Dilated:** Like local but with gaps. Captures longer range with same cost.
3. **Block-sparse:** Divide sequence into blocks; attend only within and between adjacent blocks.

### Part (c): Attention in few-shot learning (10 pts)

In few-shot classification (see our capstone project, capstone_ml_medical.md), sparse attention serves a different purpose: **regularization**. With only 5 support examples, full cross-attention between support and query embeddings can overfit. ASA-inspired sparsity forces the model to focus on the most informative support-query pairs, improving generalization.

Our capstone results: ProtoNet + CrossAttn achieves 73.5% 5-shot accuracy, while removing the sparsity constraint drops accuracy to 71.9% (see capstone_ml_medical.md, Section 4).

## Problem 3: Coding Exercise — Transformer Block (35 pts)

Implement a complete transformer encoder block:

```python
class TransformerBlock(torch.nn.Module):
    def __init__(self, d_model, num_heads, d_ff, dropout=0.1):
        super().__init__()
        self.attn = MultiHeadAttention(d_model, num_heads)
        self.norm1 = torch.nn.LayerNorm(d_model)
        self.norm2 = torch.nn.LayerNorm(d_model)
        self.ff = torch.nn.Sequential(
            torch.nn.Linear(d_model, d_ff),
            torch.nn.ReLU(),
            torch.nn.Linear(d_ff, d_model),
        )
        self.dropout = torch.nn.Dropout(dropout)

    def forward(self, x, mask=None):
        attn_out, attn_weights = self.attn(x, x, x, mask)
        x = self.norm1(x + self.dropout(attn_out))
        ff_out = self.ff(x)
        x = self.norm2(x + self.dropout(ff_out))
        return x, attn_weights
```

Test with n=128, d=256, h=8, d_ff=1024. Verify output shape is (batch, 128, 256) and attention weights sum to 1 along the key dimension.

---

*References: Vaswani et al., "Attention Is All You Need," 2017; Chen et al., "Adaptive Sparse Attention," NeurIPS 2022.*
