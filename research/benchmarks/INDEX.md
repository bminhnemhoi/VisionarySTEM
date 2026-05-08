# Benchmarks & Datasets

## Public benchmarks tham chiếu
| Name | Domain | URL | Use for VisionarySTEM |
|------|--------|-----|------------------------|
| **OmniDocBench** | PDF parsing | github.com/opendatalab/OmniDocBench | Đo accuracy parsing |
| **MathVista** | Math reasoning | mathvista.github.io | Đo math understanding |
| **MMMU** | Multimodal reasoning | mmmu-benchmark.github.io | Tổng quát multimodal |
| **ViDoRe v1/v2** | Visual document retrieval | huggingface.co/datasets/vidore | Đánh giá ColQwen2 |
| **ChartQA** | Chart understanding | github.com/vis-nlp/ChartQA | Chart description quality |
| **VLSP 2020 ASR** | Vietnamese ASR | – | PhoWhisper baseline |
| **Common Voice (vi)** | Vietnamese ASR | commonvoice.mozilla.org | STT eval |

## Tự tạo
| Dataset | Mô tả | Status |
|---------|-------|--------|
| **VN-STEM-50** | 50 trang sách giáo khoa STEM tiếng Việt + GT | ❌ chưa tạo — Sprint 3 |
| **VN-STEM-Speech-50** | 50 công thức + spoken_text gold-standard | ❌ chưa tạo — Sprint 3 |
| **sample_physics_gt** | 4 blocks F=ma | ✅ có (tests/sample_data/benchmarks/) |

## Quy ước tự đánh giá
- WER (jiwer) cho spoken_text
- CER (jiwer) cho LaTeX raw
- BLEU/ROUGE cho chart_description (so với chuyên gia khiếm thị)
- ECE / AURC cho confidence (theo MA-LED methodology)
- Latency p50, p95, p99
