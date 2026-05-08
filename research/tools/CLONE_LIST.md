# Repos cần clone để tham chiếu

> Chạy script `scripts/setup_research.py` (sẽ tạo trong Sprint 2) để clone shallow tự động.

## P1 – Bắt buộc clone ngay
| Repo | Mục đích | Lệnh |
|------|----------|------|
| VinAIResearch/PhoWhisper | STT tiếng Việt SOTA | `git clone --depth 1 https://github.com/VinAIResearch/PhoWhisper.git tools/phowhisper` |
| VikParuchuri/marker | PDF→Markdown SOTA | `git clone --depth 1 https://github.com/VikParuchuri/marker.git tools/marker` |
| VikParuchuri/surya | OCR + Latex (replace texify) | `git clone --depth 1 https://github.com/VikParuchuri/surya.git tools/surya` |
| illuin-tech/colpali | Multi-vector visual RAG | `git clone --depth 1 https://github.com/illuin-tech/colpali.git tools/colpali` |
| pnnbao97/VieNeu-TTS | TTS VN on-device | `git clone --depth 1 https://github.com/pnnbao97/VieNeu-TTS.git tools/vieneu-tts` |
| dangvansam/viet-tts | TTS VN backup | `git clone --depth 1 https://github.com/dangvansam/viet-tts.git tools/viet-tts` |

## P2 – Tham khảo kiến trúc
| Repo | Mục đích |
|------|----------|
| Madeeha-Anjum/multi-tenancy-system | FastAPI multi-tenant ref |
| huuquyet/PhoWhisper-next | PhoWhisper trên Next.js (frontend ref) |
| Meta facebookresearch/nougat | Nougat baseline |

## P3 – Accessibility tools
| Repo | Mục đích |
|------|----------|
| liblouis/liblouis | Braille translator |
| mathjax/MathJax | MathML rendering + speech |
| daisy/ace | EPUB accessibility checker |

## Cấu trúc sau khi clone
```
tools/
├── phowhisper/
│   └── WHY_USEFUL.md       # ngắn ≤100 từ
├── marker/
│   └── WHY_USEFUL.md
├── ...
└── CLONE_LIST.md (file này)
```

## Lưu ý
- Dùng `--depth 1` để giảm dung lượng (shallow clone)
- KHÔNG sửa code trong các clone — chỉ đọc tham khảo
- Nếu cần fork, tạo subfolder `tools/forks/{repo-name}` và document rõ
