/**
 * Library metadata mirrored from backend `src/data/library.py`.
 * Kept in sync manually — keep simple, no fetch on first render.
 */

export const LIBRARY_TITLES: Record<string, string> = {
  physics: "Vật lý — Định luật Newton",
  calculus: "Toán — Vi tích phân",
  linear_algebra: "Toán — Đại số tuyến tính",
  chemistry: "Hoá học — Phản ứng cơ bản",
  statistics: "Toán — Thống kê và phân phối chuẩn",
  wave_physics: "Vật lý — Sóng và dao động",
};

export const LIBRARY_INTRO_TEXT =
  "Thư viện có sáu tài liệu. " +
  "Một, Vật lý: Định luật Newton. " +
  "Hai, Toán: Vi tích phân. " +
  "Ba, Toán: Đại số tuyến tính. " +
  "Bốn, Hoá học cơ bản. " +
  "Năm, Toán: Thống kê. " +
  "Sáu, Vật lý: Sóng và dao động. " +
  "Hãy nói tên hoặc số thứ tự để tải.";
