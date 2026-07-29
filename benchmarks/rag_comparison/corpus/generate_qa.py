#!/usr/bin/env python3
"""Generate 30 ground-truth Q&A pairs for the RAG comparison benchmark."""

import json
from pathlib import Path

CORPUS_DIR = Path(__file__).parent

QA_PAIRS = [
    # ── Factual Recall (10) ───────────────────────────────────────────
    {
        "id": "fr_01",
        "type": "factual_recall",
        "question": "Who teaches CS 301 Advanced Machine Learning?",
        "answer": "Prof. Sarah Chen teaches CS 301 Advanced Machine Learning.",
        "source_docs": ["cs301_syllabus.md"],
        "difficulty": "easy",
    },
    {
        "id": "fr_02",
        "type": "factual_recall",
        "question": "What is the 5-shot classification accuracy achieved by the capstone project?",
        "answer": "The capstone project by Priya Sharma and Marcus Johnson achieved 73.5% accuracy in the 5-shot setting.",
        "source_docs": ["capstone_ml_medical.md"],
        "difficulty": "easy",
    },
    {
        "id": "fr_03",
        "type": "factual_recall",
        "question": "How many dermoscopy images are in the curated dataset used for few-shot rare disease diagnosis?",
        "answer": "The dataset contains 1,200 dermoscopy images spanning 15 dermatological conditions.",
        "source_docs": ["biomedical_ml_collab.md"],
        "difficulty": "easy",
    },
    {
        "id": "fr_04",
        "type": "factual_recall",
        "question": "What are the prerequisites for CS 201 Introduction to Machine Learning?",
        "answer": "The prerequisites for CS 201 are MATH 205 (Linear Algebra) taught by Prof. Maria Rodriguez and STAT 210 (Probability and Statistical Inference) taught by Prof. Thomas Brown.",
        "source_docs": ["cs201_syllabus.md"],
        "difficulty": "easy",
    },
    {
        "id": "fr_05",
        "type": "factual_recall",
        "question": "What PhD advisor supervised Prof. Sarah Chen's doctoral work?",
        "answer": "Prof. Sarah Chen received her Ph.D. from MIT under the supervision of Prof. David Park.",
        "source_docs": ["prof_chen_research.md"],
        "difficulty": "easy",
    },
    {
        "id": "fr_06",
        "type": "factual_recall",
        "question": "What is the computational complexity of standard scaled dot-product attention for a sequence of length n and embedding dimension d?",
        "answer": "The computational complexity of standard scaled dot-product attention is O(n^2 * d), dominated by the n^2 attention score computation.",
        "source_docs": ["homework1_solutions.md"],
        "difficulty": "medium",
    },
    {
        "id": "fr_07",
        "type": "factual_recall",
        "question": "How many parameters does the ASA-inspired music generation model use compared to the full attention baseline?",
        "answer": "The ASA-inspired music generation model uses 87M parameters, which is 39% fewer than the full attention baseline of 142M parameters.",
        "source_docs": ["project_gan_music.md"],
        "difficulty": "medium",
    },
    {
        "id": "fr_08",
        "type": "factual_recall",
        "question": "What are the three team members in Prof. Chen's lab who work on the biomedical ML collaboration?",
        "answer": "The three team members are Alex Kim, Priya Sharma, and Marcus Johnson.",
        "source_docs": ["prof_chen_research.md", "biomedical_ml_collab.md"],
        "difficulty": "easy",
    },
    {
        "id": "fr_09",
        "type": "factual_recall",
        "question": "What is the total new research funding received by the CS department in the 2025-2026 academic year?",
        "answer": "The CS department received $3.1M in total new funding, representing a 23% increase over the previous year.",
        "source_docs": ["department_report_2026.md"],
        "difficulty": "easy",
    },
    {
        "id": "fr_10",
        "type": "factual_recall",
        "question": "Who is the TA for the STAT 210 Bayesian linear regression lab?",
        "answer": "Derek Lee is the TA for the STAT 210 lab on Bayesian linear regression.",
        "source_docs": ["stat210_practical.md"],
        "difficulty": "easy",
    },

    # ── Multi-hop (10) ────────────────────────────────────────────────
    {
        "id": "mh_01",
        "type": "multi_hop",
        "question": "What mathematical concept from Prof. Rodriguez's MATH 205 course is directly applied in Prof. Chen's research on attention mechanism visualization?",
        "answer": "Eigenvalue decomposition and the spectral theorem from MATH 205 are directly applied. The spectral theorem guarantees that PCA works on symmetric covariance matrices, and Prof. Chen uses PCA to project high-dimensional attention weight matrices into lower-dimensional subspaces for visualization. Prof. Rodriguez and Prof. Chen also collaborate on using randomized SVD to analyze attention weight matrices.",
        "source_docs": ["math205_notes.md", "prof_chen_research.md", "rodriguez_research.md"],
        "difficulty": "hard",
    },
    {
        "id": "mh_02",
        "type": "multi_hop",
        "question": "How does the Bayesian inference framework from Prof. Brown's STAT 210 connect to the regularization technique used in the Prototypical Network for medical image classification?",
        "answer": "A Gaussian prior on weights corresponds to L2 (ridge) regularization, as explained in STAT 210. In the few-shot medical imaging capstone, this Bayesian perspective is key: the model treats few-shot learning as online Bayesian inference where the support set plays the role of observed data, and the class prototype is interpreted as a posterior mean. The sparse attention regularization in the capstone project can be understood as a form of Bayesian regularization that prevents overfitting with limited support examples.",
        "source_docs": ["stat210_notes.md", "stat210_practical.md", "capstone_ml_medical.md"],
        "difficulty": "hard",
    },
    {
        "id": "mh_03",
        "type": "multi_hop",
        "question": "What role does Prof. Liu's CS 201 course play in preparing students for Prof. Chen's CS 301 capstone projects?",
        "answer": "CS 201 covers foundational topics like backpropagation, neural networks, PCA, and image classification that directly prepare students for CS 301. Specifically, ResNet architectures first encountered in CS 201 serve as the backbone in the medical imaging capstone project. The top-down teaching approach in CS 201 ensures students understand WHY transformers matter before learning HOW they work in CS 301. Prof. Chen and Prof. Liu coordinate syllabi to ensure smooth transitions.",
        "source_docs": ["cs201_syllabus.md", "liu_teaching_philosophy.md", "capstone_ml_medical.md"],
        "difficulty": "medium",
    },
    {
        "id": "mh_04",
        "type": "multi_hop",
        "question": "How does Prof. Rodriguez's research on randomized SVD relate to the efficiency improvements in the music generation project?",
        "answer": "Prof. Rodriguez's randomized SVD algorithm achieves near-optimal low-rank matrix approximations in O(n^2*k) time instead of O(n^3). The music generation project by Fatima Al-Rashid and Derek Lee uses ASA-inspired sparse attention to reduce parameter count by 39%, and their conclusions mention integrating Prof. Rodriguez's randomized SVD for further efficiency gains. The sparsity patterns learned by the model were visualized using techniques from Prof. Rodriguez's research on low-rank matrix approximation.",
        "source_docs": ["rodriguez_research.md", "project_gan_music.md"],
        "difficulty": "medium",
    },
    {
        "id": "mh_05",
        "type": "multi_hop",
        "question": "Who are all the authors on the two papers in preparation from the Chen-Watson biomedical collaboration, and what are the target venues?",
        "answer": "Paper 1, 'Sparse Attention for Few-Shot Medical Image Classification,' is led by Priya Sharma and Sarah Chen, targeting MICCAI 2027. Paper 2, 'A Curated Dermoscopy Dataset for Few-Shot Learning Research,' is led by Emily Watson, Marcus Johnson, and Sarah Chen, targeting Scientific Data (Nature).",
        "source_docs": ["biomedical_ml_collab.md", "capstone_ml_medical.md"],
        "difficulty": "medium",
    },
    {
        "id": "mh_06",
        "type": "multi_hop",
        "question": "How does the concept of eigenvalue theory from MATH 205 Week 4 connect to the PCA derivation in Priya Sharma's MATH 205 HW2 and its application in Prof. Chen's CS 301?",
        "answer": "Week 4 of MATH 205 covers eigenvalues and eigenvectors, including the spectral theorem for symmetric matrices. In Priya Sharma's HW2, PCA is derived by finding eigenvectors of the covariance matrix, with the spectral theorem guaranteeing orthogonal principal components. In Prof. Chen's CS 301, PCA is applied to project high-dimensional key and value matrices into lower-dimensional spaces to reduce the O(n^2*d) attention complexity, and for visualizing attention weight matrices.",
        "source_docs": ["math205_notes.md", "hw2_linear_algebra.md", "cs301_syllabus.md"],
        "difficulty": "hard",
    },
    {
        "id": "mh_07",
        "type": "multi_hop",
        "question": "What is Derek Lee's role across the department, and how do his activities connect different courses?",
        "answer": "Derek Lee is an undergraduate student who took CS 201 with Prof. Liu (Fall 2024), is now a TA for STAT 210 with Prof. Brown, co-authored the music generation project with Fatima Al-Rashid in Prof. Chen's CS 301, and participated in the CS 490 seminar. His trajectory connects all four courses in the ML sequence.",
        "source_docs": ["liu_teaching_philosophy.md", "stat210_practical.md", "project_gan_music.md", "cs490_seminar_notes.md"],
        "difficulty": "medium",
    },
    {
        "id": "mh_08",
        "type": "multi_hop",
        "question": "How does Alex Kim's gating network architecture for ASA connect the sparse attention work to the music generation project?",
        "answer": "Alex Kim developed a residual gating network with layer normalization for ASA that achieved 94.7% accuracy on synthetic tasks. At the CS 490 seminar, Prof. Chen suggested exploring ASA for the music generation project. Alex then shared this gating network architecture with Fatima Al-Rashid and Derek Lee, who adapted it for their ASA-inspired music generation model, achieving 39% parameter reduction with comparable quality.",
        "source_docs": ["alex_kim_notes.md", "cs490_seminar_notes.md", "project_gan_music.md"],
        "difficulty": "hard",
    },
    {
        "id": "mh_09",
        "type": "multi_hop",
        "question": "How do Prof. Liu's teaching philosophy and the student survey results inform each other?",
        "answer": "Prof. Liu's top-down teaching philosophy (start with intuition, build to rigor) is validated by survey results: 91% of students felt well-prepared for CS 301, and students specifically praised understanding WHY transformers matter before learning HOW. Prof. Liu received the highest relevance-of-examples rating (4.8/5). The survey also identified areas for improvement that align with Liu's future goals, such as expanding cross-listed courses and developing clinical AI tracks.",
        "source_docs": ["liu_teaching_philosophy.md", "student_survey_2025.md"],
        "difficulty": "medium",
    },
    {
        "id": "mh_10",
        "type": "multi_hop",
        "question": "What is the federated PCA collaboration between Rodriguez and Liu, and how does it relate to the privacy themes in Prof. Chen's biomedical work?",
        "answer": "Prof. Rodriguez and Prof. Liu collaborate on federated PCA — computing principal components across distributed data sources without centralizing data, with a paper under review at KDD 2026. This connects to Prof. Chen's biomedical collaboration through the theme of privacy-preserving data analysis: the dermoscopy dataset required IRB approval and de-identification, and federated learning (Liu's proposed new course CS 350) could enable multi-center validation without sharing patient data.",
        "source_docs": ["rodriguez_research.md", "biomedical_ml_collab.md", "department_report_2026.md"],
        "difficulty": "hard",
    },

    # ── Synthesis (10) ────────────────────────────────────────────────
    {
        "id": "syn_01",
        "type": "synthesis",
        "question": "Compare the teaching philosophies of Prof. Chen and Prof. Liu. How do their approaches complement each other in the ML curriculum?",
        "answer": "Prof. Liu uses a top-down, application-first approach: starting with real problems, building intuition, then formalizing mathematics. He emphasizes authentic assessment and curriculum coherence. Prof. Chen emphasizes research-driven teaching, having students engage with cutting-edge papers and capstone projects that address real-world problems (e.g., medical imaging). Their approaches complement each other: Liu provides broad foundational skills through structured coursework, while Chen provides deep specialization through research projects. The curriculum is deliberately sequenced — Liu's CS 201 builds the foundation (backpropagation, basic models), and Chen's CS 301 builds advanced tools (transformers, sparse attention). They coordinate syllabi each semester.",
        "source_docs": ["liu_teaching_philosophy.md", "cs301_syllabus.md", "cs201_syllabus.md", "student_survey_2025.md"],
        "difficulty": "hard",
    },
    {
        "id": "syn_02",
        "type": "synthesis",
        "question": "Evaluate the interdisciplinary collaboration model between the CS and Biomedical Engineering departments. What makes it effective?",
        "answer": "The Chen-Watson collaboration is effective because it combines complementary expertise: Chen provides algorithmic innovation (ASA, few-shot learning), Watson provides clinical domain knowledge and data access. Key success factors include: (1) Natural student pipeline through BME 305 guest lectures, (2) Shared infrastructure (IRB-approved dataset of 1,200 images), (3) Clear authorship delineation across two papers targeting different venues (MICCAI for algorithms, Scientific Data for the dataset), (4) Multi-role team members (Alex Kim handles attention, Priya handles meta-learning, Marcus handles image processing), and (5) Strong funding ($650K NIH R21 + $1.2M NSF). The collaboration model has been recognized by the department as a model for interdisciplinary work.",
        "source_docs": ["biomedical_ml_collab.md", "watson_biomed_notes.md", "department_report_2026.md"],
        "difficulty": "hard",
    },
    {
        "id": "syn_03",
        "type": "synthesis",
        "question": "Based on the student survey, department report, and individual research profiles, assess the overall health and trajectory of the ML program.",
        "answer": "The ML program shows strong health across multiple dimensions: enrollment is growing rapidly (35% in CS 201, 38% in CS 301), research funding increased 23% to $3.1M, student satisfaction averages 4.3/5.0, and 88% would recommend the sequence. Students achieve notable outcomes (NeurIPS workshop, best paper awards, ACM competitions). The curriculum is well-integrated with explicit cross-course connections. The program's trajectory is upward: new courses planned (CS 350 Federated Learning), industry partnerships emerging, and interdisciplinary collaborations producing high-impact papers. Areas for improvement include making MATH 205 more computational and better integrating STAT 210 with ML applications, both of which are being addressed by faculty coordination.",
        "source_docs": ["student_survey_2025.md", "department_report_2026.md", "prof_chen_research.md", "rodriguez_research.md"],
        "difficulty": "hard",
    },
    {
        "id": "syn_04",
        "type": "synthesis",
        "question": "How does the concept of sparsity manifest across different projects in the ML program, from Prof. Rodriguez's mathematical foundations to practical applications?",
        "answer": "Sparsity manifests at multiple levels: (1) Mathematically, Prof. Rodriguez's randomized SVD provides low-rank (sparse) approximations of large matrices. (2) Algorithmically, Prof. Chen's ASA framework introduces sparsity into attention by selecting only top-k key positions per query. (3) In the medical imaging capstone, sparsity regularizes cross-attention between support examples, preventing overfitting. (4) In music generation, ASA-inspired sparsity reduces parameters by 39% while maintaining quality. (5) The learned sparsity patterns are interpretable — capturing linguistically meaningful structures in text, repetition and harmony in music, and diagnostic features in medical images. This progression from mathematical theory to diverse applications demonstrates the depth and coherence of the ML program's research agenda.",
        "source_docs": ["rodriguez_research.md", "prof_chen_research.md", "capstone_ml_medical.md", "project_gan_music.md", "hw3_transformers.md"],
        "difficulty": "hard",
    },
    {
        "id": "syn_05",
        "type": "synthesis",
        "question": "Analyze the role of the Prototypical Network architecture across the capstone project, the research essay, and the guest lecture. How do these different perspectives enrich understanding?",
        "answer": "Three documents provide complementary perspectives on Prototypical Networks: (1) The research essay (by Priya Sharma) places ProtoNets in historical context alongside Siamese Nets, Matching Nets, and MAML, analyzing their relative strengths. (2) The capstone project (by Sharma and Johnson) extends ProtoNets with cross-attention and ASA sparsity, providing empirical validation on real medical data (73.5% 5-shot). (3) The guest lecture (by Prof. Chen in Watson's BME 305) interprets ProtoNets through a Bayesian lens — the class prototype as a posterior mean, few-shot learning as online Bayesian inference. Together, these perspectives cover theory (literature review), engineering (capstone implementation), and conceptual interpretation (guest lecture), providing a complete understanding of the architecture.",
        "source_docs": ["research_essay_few_shot.md", "capstone_ml_medical.md", "watson_biomed_notes.md"],
        "difficulty": "hard",
    },
    {
        "id": "syn_06",
        "type": "synthesis",
        "question": "What ethical considerations arise from the intersection of AI-assisted medical diagnosis and the few-shot learning approach used in the Chen-Watson collaboration?",
        "answer": "Several ethical considerations emerge: (1) With only 1,200 images across 15 conditions, the model may not generalize to underrepresented populations — the IRB approval (Protocol #2025-0847) addresses data privacy but not algorithmic bias. (2) The 73.5% 5-shot accuracy, while impressive, means ~26.5% error rate, which may be unacceptable for clinical deployment without uncertainty quantification. (3) The collaborative model raises questions about responsibility — if the model misdiagnoses, liability falls on the clinical team (Watson), not the algorithm developers (Chen). (4) The guest lecture mentions developing uncertainty estimation for out-of-distribution inputs, which is essential for safe clinical use. (5) Prof. Liu's emphasis on ethics in CS 201 provides a foundational framework, but specific guidelines for medical AI need further development.",
        "source_docs": ["biomedical_ml_collab.md", "capstone_ml_medical.md", "watson_biomed_notes.md", "cs201_syllabus.md"],
        "difficulty": "hard",
    },
    {
        "id": "syn_07",
        "type": "synthesis",
        "question": "How does the scaling laws discussion from CS 490 inform the practical decisions made in the medical imaging and music generation projects?",
        "answer": "The CS 490 seminar on scaling laws revealed that sparsity becomes more valuable as models grow — Alex Kim's ASA results show increasing gains at larger scales. This directly informs both projects: In medical imaging, the team tested ViT-Small as well as ResNet-18, achieving 76.8% 5-shot with ViT (vs. 73.5% with ResNet-18), suggesting that scaling the backbone benefits from sparse attention. In music generation, the ASA-inspired approach achieved 39% parameter reduction with quality matching full attention. The Chinchilla-optimal scaling insight also raises a question: could fewer parameters with better data efficiency (via sparsity) outperform larger models with more data? This is a promising direction for both projects' future work.",
        "source_docs": ["cs490_seminar_notes.md", "alex_kim_notes.md", "capstone_ml_medical.md", "project_gan_music.md"],
        "difficulty": "hard",
    },
    {
        "id": "syn_08",
        "type": "synthesis",
        "question": "Assess the completeness and coherence of the ML course sequence (MATH 205, STAT 210, CS 201, CS 301) based on all available evidence in the corpus.",
        "answer": "The ML course sequence demonstrates remarkable coherence: MATH 205 provides linear algebra foundations (eigenvalues, SVD, vector spaces) that directly support PCA in CS 201 and attention analysis in CS 301. STAT 210's Bayesian inference framework connects to regularization in CS 201 and provides theoretical grounding for few-shot learning in CS 301. CS 201 bridges to CS 301 through backpropagation, neural networks, and basic optimization. The sequence is validated by: (1) 88% of survey respondents agreeing prerequisites are well-aligned, (2) Prof. Chen and Prof. Liu coordinating syllabi, (3) students like Priya Sharma successfully progressing from CS 201 through CS 301 to PhD research, and (4) cross-references in documents showing explicit connections (e.g., hw2 references CS 301 applications, stat210_practical references CS 201). The only gaps identified are: MATH 205 needs more programming assignments, and STAT 210 needs more ML-specific examples.",
        "source_docs": ["math205_notes.md", "stat210_notes.md", "cs201_syllabus.md", "cs301_syllabus.md", "student_survey_2025.md", "liu_teaching_philosophy.md"],
        "difficulty": "hard",
    },
    {
        "id": "syn_09",
        "type": "synthesis",
        "question": "How does the research output from Prof. Chen's lab (publications, collaborations, student achievements) reflect the effectiveness of the training pipeline from CS 201 through PhD research?",
        "output": "Prof. Chen's lab produces significant research output: the ASA paper (340+ citations), the biomedical collaboration (two papers in preparation), and student achievements (NeurIPS workshop, best paper award, ACM competition). This reflects an effective training pipeline: Priya Sharma progressed from CS 201 (Fall 2023) through literature review to capstone to PhD research. Alex Kim built from ASA foundations to medical imaging applications. Marcus Johnson advanced from MS capstone to biomedical collaboration authorship. The pipeline works because: (1) CS 201 provides broad foundations, (2) CS 301 provides advanced tools and research exposure, (3) capstone projects address real problems with real collaborators (Watson), and (4) the interdisciplinary environment (Rodriguez, Liu, Watson) provides diverse perspectives. The department report confirms this: 47 publications, $3.1M funding, and 5 notable student achievements in one year.",
        "source_docs": ["prof_chen_research.md", "department_report_2026.md", "capstone_ml_medical.md", "alex_kim_notes.md", "liu_teaching_philosophy.md"],
        "difficulty": "hard",
    },
    {
        "id": "syn_10",
        "type": "synthesis",
        "question": "Based on the entire corpus, what are the most promising future directions for the ML program, and how do the different faculty members' expertise contribute to these directions?",
        "answer": "The most promising future directions, synthesized from across the corpus, include: (1) Clinical AI deployment — Chen's few-shot learning + Watson's clinical validation + Rodriguez's dimensionality reduction + NSF/NIH funding. (2) Federated learning for healthcare — Liu and Rodriguez's federated PCA work + proposed CS 350 course + privacy-preserving multi-center medical studies. (3) Efficient transformers at scale — Chen's ASA + Rodriguez's randomized SVD + scaling law insights from CS 490 seminar. (4) Curriculum expansion — new CS 350, expanded CS 201 sections, LLM fundamentals in CS 201, summer bootcamp. (5) Industry partnerships — healthcare AI companies for clinical validation. Each faculty member contributes unique expertise: Chen in algorithms, Liu in pedagogy and federated systems, Rodriguez in mathematical foundations, Brown in statistical theory. The interdisciplinary collaboration model (exemplified by Chen-Watson) provides a template for future partnerships.",
        "source_docs": ["department_report_2026.md", "liu_teaching_philosophy.md", "rodriguez_research.md", "biomedical_ml_collab.md", "cs490_seminar_notes.md", "student_survey_2025.md"],
        "difficulty": "hard",
    },
]


def main():
    manifest_path = CORPUS_DIR / "manifest.json"
    if not manifest_path.exists():
        print("ERROR: manifest.json not found. Run generate_corpus.py first.")
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["qa_pairs"] = QA_PAIRS

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Added {len(QA_PAIRS)} Q&A pairs to manifest.json")
    types = {}
    for q in QA_PAIRS:
        types[q["type"]] = types.get(q["type"], 0) + 1
    for t, count in sorted(types.items()):
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
