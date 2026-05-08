# Vietnamese TTS & STT (April 2026)

## TTS so sánh

| Engine | Quality | License | Voice cloning | Latency | Khuyến nghị |
|--------|---------|---------|---------------|---------|-------------|
| **Edge TTS (vi-VN-HoaiMyNeural)** | Tốt | Free, MS Azure | ❌ | Thấp (cloud) | **GIỮ** cho free tier |
| **VieNeu-TTS** | Rất tốt 24kHz | MIT | ✅ instant | CPU OK | **THÊM** cho premium tier (on-device) |
| **VietTTS (dangvansam)** | Rất tốt | Apache 2.0 | ✅ | GPU recommended | Backup option |
| **Viettel TTS** | 95% real human | Commercial paid | ❌ | Cloud | Cho B2B premium VN |
| **MiniMax Audio** | Top quality | Commercial | ✅ | Cloud | Quốc tế hoá |
| **ElevenLabs (vi)** | Top quality | Commercial | ✅ | Cloud | Premium global |

## STT (cần thêm cho voice query)
| Engine | WER tiếng Việt | License | Notes |
|--------|----------------|---------|-------|
| **PhoWhisper-medium** (VinAI) | SOTA mở | MIT | Fine-tune 844h — tốt nhất open-source |
| PhoWhisper-large | Best accuracy, chậm | MIT | Cho premium |
| OpenAI Whisper-large-v3 | Trung bình | MIT | Đa ngôn ngữ |
| Google Speech-to-Text | Tốt | Paid | Latency thấp |
| Viettel ASR | Tốt | Paid | B2B VN |

## Khuyến nghị tích hợp VisionarySTEM
1. **Tier free**: Edge TTS + Whisper-base (server-side)
2. **Tier Pro**: VieNeu-TTS on-device + PhoWhisper-medium (giảm latency, privacy)
3. **Tier Enterprise**: Viettel TTS/ASR (SLA + fapiao + tiếng Việt accent miền)
4. **Voice query flow**:
   ```
   Mic record → STT (PhoWhisper) → query text → Spatial RAG → spoken_answer → TTS → Audio
   ```

## Code/repo cần clone
- `git clone https://github.com/VinAIResearch/PhoWhisper tools/phowhisper`
- `git clone https://github.com/pnnbao97/VieNeu-TTS tools/vieneu-tts`
- `git clone https://github.com/dangvansam/viet-tts tools/viet-tts`
- HF model: `vinai/PhoWhisper-medium`, `vinai/PhoWhisper-large`

## Sources
- [PhoWhisper VinAI](https://github.com/VinAIResearch/PhoWhisper)
- [PhoWhisper paper arXiv 2406.02555](https://arxiv.org/abs/2406.02555)
- [VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS)
- [VietTTS](https://github.com/dangvansam/viet-tts)
- [Viettel TTS](https://viettelai.vn/en/chuyen-giong-noi)
