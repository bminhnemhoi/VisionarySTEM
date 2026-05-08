/**
 * Vietnamese voice command grammar for VisionarySTEM.
 *
 * Maps natural Vietnamese utterances → intent + parameters.
 * Designed for sinh viên khiếm thị: lệnh ngắn, dễ nói, không yêu cầu format chính xác.
 *
 * Patterns được support:
 * - Bắt đầu: "tài liệu mẫu", "demo", "tải file", "mở file", "đọc thử"
 * - Phát/dừng: "đọc đi", "tạm dừng", "dừng", "đọc tiếp", "tiếp tục"
 * - Tua: "tua lui [N giây]", "tua tới [N giây]", "lui 10 giây"
 * - Lặp: "đọc lại", "lặp lại", "nói lại"
 * - Hỏi: "phần này là gì", "giải thích", "đơn giản hơn", "cho ví dụ"
 * - Điều khiển: "tắt mic", "bật mic", "giúp đỡ"
 */

export type VoiceIntent =
  | { kind: "load_mock" }
  | { kind: "upload_file" }
  | { kind: "play" }
  | { kind: "pause" }
  | { kind: "resume" }
  | { kind: "replay_block" }
  | { kind: "seek"; deltaSeconds: number }
  | { kind: "ask_focus_block"; question: string }
  | { kind: "ask_simpler" }
  | { kind: "ask_example" }
  | { kind: "filter_blocks"; type: "math" | "chart" | "table" | "figure" | "text" }
  | { kind: "next_block" }
  | { kind: "prev_block" }
  | { kind: "repeat_last" }
  | { kind: "mute" }
  | { kind: "unmute" }
  | { kind: "help" }
  | { kind: "stop_all" }
  | { kind: "summarize" }
  | { kind: "skip_welcome" }                       // Cắt phần chào / hướng dẫn
  | { kind: "upload_ask_source" }                  // Mơ hồ — AI hỏi "từ máy hay từ link?"
  | { kind: "upload_url"; url?: string }           // Tải PDF từ URL
  | { kind: "library_browse" }                     // Liệt kê thư viện mẫu
  | { kind: "library_load"; slug: string }         // Tải 1 sample cụ thể
  | { kind: "web_search"; query: string }          // Tìm trên mạng (Gemini grounding)
  | { kind: "agent_run"; request: string }         // Multi-step planner (compound request)
  | { kind: "export_epub" }                        // Tải EPUB3 file về máy (offline reading)
  | { kind: "export_braille" }                     // Tải Braille Unicode text về máy
  | { kind: "sonify_chart"; block_index?: number } // Nghe biểu đồ ra nhạc (sonification)
  | { kind: "free_chat"; question: string };       // Fallback → tutor / general assist

interface CommandPattern {
  /** Regex hoặc array các synonym phải xuất hiện */
  match: RegExp | string[];
  /** Build intent từ matched groups */
  build: (text: string, match?: RegExpMatchArray) => VoiceIntent;
}

// Helper: text contains all words (any order)
function containsAll(text: string, words: string[]): boolean {
  return words.every((w) => text.includes(w));
}
// Helper: text contains any of the words
function containsAny(text: string, words: string[]): boolean {
  return words.some((w) => text.includes(w));
}

const PATTERNS: CommandPattern[] = [
  // ============ SKIP WELCOME (highest priority — must come before others) ============
  {
    match: /^bỏ qua$|bỏ qua đi|bỏ qua phần|bỏ qua giới thiệu|^skip$|đủ rồi|tôi (biết|hiểu) rồi|tôi nghe nhiều lần rồi|cắt phần (chào|giới thiệu)/,
    build: () => ({ kind: "skip_welcome" }),
  },

  // ============ WEB SEARCH (Phase 2) — phải đứng TRƯỚC library/upload patterns ============
  // Match "tìm trên mạng / tìm tài liệu / search / google / có tài liệu nào về..." + topic.
  // Trả về intent web_search với query = phần topic.
  // ƯU TIÊN cao nhất sau skip_welcome — nếu user nói "tìm trên mạng X", X có thể chứa
  // từ matches library (vật lý/vi tích phân/v.v.) nhưng intent là search, không phải library.
  {
    match:
      /(tìm (kiếm )?(trên )?(mạng|internet|google|web)|tìm (cho |giúp )?(tôi |tớ |mình )?(tài liệu|bài|nội dung|thông tin)|^google (giúp|cho tôi|tìm)|^search |có (tài liệu|bài|nội dung|gì) nào (về|nói về))/,
    build: (text) => {
      // Extract topic: bỏ phần lệnh, còn lại là query
      const stripPatterns: RegExp[] = [
        /^.*?(tìm (kiếm )?(trên )?(mạng|internet|google|web)\s*(về|cho|giúp)?\s*(tôi|tớ|mình)?\s*)/,
        /^.*?(tìm (cho |giúp )?(tôi |tớ |mình )?(tài liệu|bài|nội dung|thông tin)?\s*(về|cho|giúp)?\s*)/,
        /^.*?(google (giúp |cho |tìm )?(tôi |tớ |mình )?)/,
        /^.*?(search (cho |giúp )?(tôi |tớ |mình )?)/,
        /^.*?(có (tài liệu|bài|nội dung|gì) nào (về |nói về )?)/,
      ];
      let query = text;
      for (const p of stripPatterns) {
        const stripped = query.replace(p, "").trim();
        if (stripped && stripped.length < query.length) {
          query = stripped;
          break;
        }
      }
      if (!query || query.length < 2) query = text;
      return { kind: "web_search", query };
    },
  },

  // ============ LIBRARY (sample documents) ============
  {
    match: /^thư viện$|thư viện mẫu|tài liệu (có gì|nào|sẵn)|danh sách (tài liệu|sách)|có (gì|sách gì) (để học|sẵn)/,
    build: () => ({ kind: "library_browse" }),
  },
  // Library — load by topic name (sinh viên nói tên chủ đề)
  {
    match: /(tài liệu |sách |môn |học |nghe |đọc )?(vật lý|định luật newton|niu-tơn)/,
    build: () => ({ kind: "library_load", slug: "physics" }),
  },
  {
    match: /(tài liệu |sách |môn |học |nghe |đọc )?(vi tích phân|tích phân|đạo hàm|calculus)/,
    build: () => ({ kind: "library_load", slug: "calculus" }),
  },
  {
    match: /(tài liệu |sách |môn |học |nghe |đọc )?(đại số|ma trận|tuyến tính|linear)/,
    build: () => ({ kind: "library_load", slug: "linear_algebra" }),
  },
  {
    match: /(tài liệu |sách |môn |học |nghe |đọc )?(hoá|hóa học|chemistry)/,
    build: () => ({ kind: "library_load", slug: "chemistry" }),
  },
  {
    match: /(tài liệu |sách |môn |học |nghe |đọc )?(thống kê|xác suất|statistics)/,
    build: () => ({ kind: "library_load", slug: "statistics" }),
  },
  {
    match: /(tài liệu |sách |môn |học |nghe |đọc )?(sóng|dao động|wave)/,
    build: () => ({ kind: "library_load", slug: "wave_physics" }),
  },
  // ============ SONIFY CHART (PHẢI đứng TRƯỚC library by-ordinal) ============
  // Vì "biểu đồ số 5" có "số 5" sẽ match library_load nếu sonify đứng sau.
  {
    match: /nghe (cái )?biểu đồ|sonify|biểu đồ (phần|số) (\d+)|chuyển biểu đồ (sang|thành) (âm|nhạc)|cho tôi nghe biểu đồ/,
    build: (text) => {
      const m = text.match(/(?:phần|số)\s*(\d+)/);
      const idx = m ? parseInt(m[1], 10) : undefined;
      return { kind: "sonify_chart", block_index: idx };
    },
  },

  // Library — load by ordinal "số 1", "thứ 2", "1", "2"...
  {
    match: /^(số |thứ |bài |sample )?([1-6])$|(số|thứ|bài|sample) ([1-6])\b/,
    build: (text) => {
      const m = text.match(/([1-6])/);
      const n = m ? parseInt(m[1], 10) : 1;
      const slugs = ["physics", "calculus", "linear_algebra", "chemistry", "statistics", "wave_physics"];
      return { kind: "library_load", slug: slugs[n - 1] };
    },
  },

  // ============ EXPORT EPUB3 / BRAILLE (hidden gems showcase) ============
  {
    match: /xuất (file )?(e[\s-]?pub|epub3?|sách điện tử)|tải (file )?(e[\s-]?pub|sách điện tử)|lưu (e[\s-]?pub|sách điện tử)|export (e[\s-]?pub|epub)/,
    build: () => ({ kind: "export_epub" }),
  },
  {
    match: /xuất (file )?(braille|chữ nổi)|tải (braille|chữ nổi)|in (chữ nổi|braille)|export braille/,
    build: () => ({ kind: "export_braille" }),
  },

  // ============ URL UPLOAD (specific — phải nhắc rõ "link" / "url") ============
  {
    match: /tải link|tải url|từ link|từ url|phân tích link|phân tích url|có (một |1 )?link|có (một |1 )?url|^link$|^url$/,
    build: () => ({ kind: "upload_url" }),
  },

  // ============ FROM MACHINE — disambiguation reply (phải đứng TRƯỚC upload_ask_source) ============
  // Khi AI vừa hỏi "từ máy hay từ link", user nói "từ máy" → mở file picker
  {
    match: /^(từ )?máy( của tôi| mình| tính)?$|trên máy|từ máy tính|từ thiết bị|^(file|tệp) của tôi$/,
    build: () => ({ kind: "upload_file" }),
  },

  // ============ AMBIGUOUS UPLOAD — AI hỏi lại nguồn ============
  // User nói "tôi muốn gửi tài liệu" / "có tài liệu" / "cách tải" → AI hỏi "từ máy hay từ link?"
  {
    match: /muốn (gửi|đưa|tải lên|upload|cho bạn) (tài liệu|file|sách|tệp|cái này|nội dung|tư liệu|bài|chương)|tôi (có|muốn) (tài liệu|file|sách|một (file|tài liệu))|gửi (cho bạn|tài liệu|file|cái này|nội dung)|đưa (cho bạn|tài liệu)|cách (tải|gửi|upload)|làm sao (để )?(tải|gửi|upload)/,
    build: () => ({ kind: "upload_ask_source" }),
  },

  // ============ LOAD MOCK / SAMPLE ============
  {
    match: ["mẫu"],
    build: () => ({ kind: "load_mock" }),
  },
  {
    match: /^demo$|^thử$|tài liệu thử|tài liệu mẫu/,
    build: () => ({ kind: "load_mock" }),
  },

  // ============ UPLOAD FILE — specific commands (nhắc rõ "file" hoặc "máy") ============
  {
    match: /tải (file|tệp)|tải tài liệu (mới|của tôi|từ máy)|mở (file|tệp|tài liệu)|^upload$|chọn file|tài liệu mới/,
    build: () => ({ kind: "upload_file" }),
  },

  // ============ HELP ============
  {
    match: /giúp đỡ|giúp tôi|tôi (có thể|nói được)|hướng dẫn|làm sao/,
    build: () => ({ kind: "help" }),
  },

  // ============ STOP ALL / MUTE ============
  {
    match: /tắt (mic|micro|microphone|nghe)|dừng nghe|im đi/,
    build: () => ({ kind: "mute" }),
  },
  {
    match: /bật (mic|micro|microphone|nghe)|nghe lại đi/,
    build: () => ({ kind: "unmute" }),
  },
  {
    match: /dừng tất cả|tắt hết|stop tất cả/,
    build: () => ({ kind: "stop_all" }),
  },

  // ============ PLAYBACK CONTROL ============
  {
    match: /tạm dừng|tạm ngưng|pause/,
    build: () => ({ kind: "pause" }),
  },
  {
    match: /^dừng$|dừng đi|dừng lại/,
    build: () => ({ kind: "pause" }),
  },
  {
    match: /^tiếp tục$|tiếp tục đi|tiếp tục đọc|(đọc|nghe|chạy) (tiếp|lại đi)/,
    build: () => ({ kind: "resume" }),
  },
  {
    match: /^(đọc|nghe|chạy)( đi)?$|bắt đầu (đọc|phát|nghe)/,
    build: () => ({ kind: "play" }),
  },
  {
    match: /đọc lại|lặp lại|nói lại|nhắc lại/,
    build: () => ({ kind: "replay_block" }),
  },
  {
    match: /câu vừa rồi|vừa nói gì|bạn nói gì/,
    build: () => ({ kind: "repeat_last" }),
  },

  // ============ SEEK ============
  {
    match: /tua lui (\d+)? ?(giây|s)?|lui (\d+)? ?(giây|s)?|quay lại (\d+)? ?(giây|s)?/,
    build: (text) => {
      const m = text.match(/(\d+)/);
      const n = m ? parseInt(m[1], 10) : 10;
      return { kind: "seek", deltaSeconds: -n };
    },
  },
  {
    match: /tua tới (\d+)? ?(giây|s)?|tới (\d+)? ?(giây|s)?|tiến (\d+)? ?(giây|s)?|nhảy (\d+)? ?(giây|s)?/,
    build: (text) => {
      const m = text.match(/(\d+)/);
      const n = m ? parseInt(m[1], 10) : 10;
      return { kind: "seek", deltaSeconds: n };
    },
  },

  // ============ NEXT / PREV BLOCK ============
  {
    match: /(block|phần|đoạn) (sau|tiếp theo|kế tiếp)|đến (cái|phần) (sau|tiếp)/,
    build: () => ({ kind: "next_block" }),
  },
  {
    match: /(block|phần|đoạn) (trước|trước đó)|về (cái|phần) trước|quay về phần trước/,
    build: () => ({ kind: "prev_block" }),
  },

  // ============ FILTER BY TYPE ============
  {
    match: /(đọc|nghe|cho tôi nghe) (tất cả )?(các )?công thức( toán)?/,
    build: () => ({ kind: "filter_blocks", type: "math" }),
  },
  {
    match: /(đọc|nghe|cho tôi nghe) (tất cả )?(các )?biểu đồ/,
    build: () => ({ kind: "filter_blocks", type: "chart" }),
  },
  {
    match: /(đọc|nghe|cho tôi nghe) (tất cả )?(các )?bảng/,
    build: () => ({ kind: "filter_blocks", type: "table" }),
  },

  // ============ ASK ABOUT FOCUS BLOCK ============
  {
    match: /phần này (là gì|nói gì|có gì|ý nghĩa|nghĩa là)|giải thích phần này|cái này (là gì|là cái gì)/,
    build: (text) => ({ kind: "ask_focus_block", question: text }),
  },

  // ============ SIMPLIFY / EXAMPLE ============
  {
    match: /^đơn giản hơn$|đơn giản hơn đi|(giải thích|nói|nói lại) (đơn giản|dễ hiểu) hơn|đơn giản hóa/,
    build: () => ({ kind: "ask_simpler" }),
  },
  {
    match: /^cho ví dụ$|cho (tôi|em|mình)? ?(một |1 )?ví dụ|ví dụ thực tế|ví dụ cụ thể/,
    build: () => ({ kind: "ask_example" }),
  },

  // ============ SUMMARIZE ============
  {
    match: /tóm tắt|tóm lược|tổng kết|nói chung là gì/,
    build: () => ({ kind: "summarize" }),
  },
];

/**
 * Question markers — nếu utterance chứa các từ này, nó là CÂU HỎI, không
 * phải command. Bypass command matching, gửi thẳng free_chat / tutor.
 *
 * Ví dụ: "cho tôi ví dụ về tải link" → KHÔNG match upload_url, → free_chat.
 *        "tải link" (đơn lẻ) → vẫn match upload_url.
 */
const QUESTION_MARKERS = [
  "ví dụ",
  "là gì",
  "là sao",
  "thế nào",
  "tại sao",
  "vì sao",
  "khi nào",
  "ở đâu",
  "có thể nào",
  "nghĩa là",
  "cho tôi biết",
  "cho mình biết",
  "kể cho",
  "giải thích về",
  "nói về",
  "nói cho",
];

/**
 * Phonetic mishears — Vietnamese ASR thường nhầm các từ tiếng Anh.
 * Áp dụng PRE-NORMALIZE để chuyển về dạng chuẩn trước khi match grammar.
 */
const PHONETIC_NORMALIZE: Array<[RegExp, string]> = [
  [/\btải li[êe]n\b/g, "tải link"],            // "tải liên" → "tải link"
  [/\b(yu|u) r[ôồ]\b/g, "url"],                // "yu rồ" → "url"
  [/\bpi đi (ép|f)\b/g, "pdf"],                // "pi đi ép" → "pdf"
  [/\b(phai|fai|phây)\b/g, "file"],            // "phai" → "file"
  [/\bvi-?z[hơâ]n( ary)? ?st(em|im)?\b/g, "visionarystem"],
  [/\b(niu|nu|nhu)-?t[ơo]n\b/g, "newton"],     // already in voice context
];

/**
 * ACTION intents: thực sự thực hiện một hành động (load doc, play audio, mở dialog).
 * Khi user dùng dạng câu hỏi ("cho tôi ví dụ về tải link"), KHÔNG nên trigger action
 * nhầm — phải route sang free_chat để giải thích.
 *
 * Các intent KHÁC (ask_focus_block, summarize, help...) vốn là câu hỏi → giữ nguyên.
 */
const ACTION_INTENTS = new Set<VoiceIntent["kind"]>([
  "load_mock",
  "upload_file",
  "upload_url",
  "upload_ask_source",
  "library_browse",
  "library_load",
  "web_search",
  "export_epub",
  "export_braille",
  "sonify_chart",
  "play",
  "pause",
  "resume",
  "seek",
  "next_block",
  "prev_block",
  "filter_blocks",
  "stop_all",
  "skip_welcome",
  "mute",
  "unmute",
  "replay_block",
]);

/**
 * Match a Vietnamese utterance to a voice intent.
 *
 * - Lowercase + strip punctuation
 * - Apply phonetic normalization (tải liên → tải link)
 * - Run command pattern matching
 * - Smart override: nếu match ACTION intent NHƯNG utterance có question marker
 *   ("ví dụ", "là gì"...) trong câu DÀI ≥ 4 từ → override sang free_chat
 *   (user đang hỏi về action chứ không yêu cầu thực hiện)
 * - Fallback to `free_chat`
 */
export function parseVoiceCommand(utterance: string): VoiceIntent | null {
  let text = utterance.toLowerCase().trim().replace(/[.,!?;:]/g, "");
  if (text.length < 2) return null;

  // Pre-normalize phonetic mishears
  for (const [pat, repl] of PHONETIC_NORMALIZE) {
    text = text.replace(pat, repl);
  }

  const isLongQuestion =
    QUESTION_MARKERS.some((m) => text.includes(m)) && text.split(/\s+/).length >= 4;

  // ============ AGENT_RUN heuristic (Phase 3) — chạy TRƯỚC pattern match ============
  // Compound request: utterance ≥6 từ + có conjunction (và/rồi/sau đó) + ≥1 action verb →
  // gửi qua planner. Note: KHÔNG dùng regex \b vì \b là ASCII boundary,
  // không match Vietnamese chars. Dùng includes() đơn giản và đáng tin cậy hơn.
  const wordCount = text.split(/\s+/).filter((w) => w.length > 0).length;
  const CONJUNCTIONS = ["và", "rồi", "sau đó", "tiếp theo", "sau khi", "với cả"];
  const ACTION_VERBS = [
    "tìm", "tải", "đọc", "mở", "phân tích", "tóm tắt", "nghe", "xem", "kiếm",
    "search", "google",
  ];
  const hasConjunction = CONJUNCTIONS.some((c) => text.includes(c));
  const actionVerbCount = ACTION_VERBS.filter((v) => text.includes(v)).length;
  // Compound: nhiều từ + có và/rồi + ít nhất 1 verb (hoặc 2+ verbs để chắc)
  const isCompoundRequest =
    hasConjunction && wordCount >= 6 && actionVerbCount >= 1 && !isLongQuestion;
  if (isCompoundRequest) {
    return { kind: "agent_run", request: utterance.trim() };
  }

  for (const pattern of PATTERNS) {
    let intent: VoiceIntent | null = null;
    if (pattern.match instanceof RegExp) {
      const m = text.match(pattern.match);
      if (m) intent = pattern.build(text, m);
    } else if (Array.isArray(pattern.match)) {
      if (containsAll(text, pattern.match)) intent = pattern.build(text);
    }
    if (!intent) continue;

    // Smart override: ACTION intent nhúng trong câu hỏi dài → free_chat
    if (ACTION_INTENTS.has(intent.kind) && isLongQuestion) {
      return { kind: "free_chat", question: utterance.trim() };
    }
    return intent;
  }

  // Fallback: treat as free chat question to tutor
  return { kind: "free_chat", question: utterance.trim() };
}

/**
 * Get a Vietnamese spoken description of all available commands (for "giúp đỡ").
 */
export function getHelpText(): string {
  return [
    "Đây là các lệnh bạn có thể nói:",
    "Để tải tài liệu: 'tài liệu mẫu' để nghe demo, 'thư viện' để chọn từ sáu sách mẫu, 'tải file' để mở từ máy bạn, hoặc 'tải link' để dán URL.",
    "Điều khiển nghe: 'đọc đi', 'tạm dừng', 'đọc tiếp', 'đọc lại', 'tua lui mười giây', 'tua tới năm giây'.",
    "Hỏi về nội dung: 'phần này là gì', 'đơn giản hơn', 'cho ví dụ', hoặc bất cứ câu hỏi nào.",
    "Lọc: 'đọc tất cả công thức', 'đọc biểu đồ', 'block tiếp theo', 'block trước'.",
    "Khác: 'tóm tắt', 'tắt mic', 'dừng tất cả', 'bỏ qua' để dừng phần chào, 'giúp đỡ'.",
    "Bạn cũng có thể đặt bất kỳ câu hỏi nào bằng tiếng Việt — tôi sẽ trả lời như người thật.",
  ].join(" ");
}
