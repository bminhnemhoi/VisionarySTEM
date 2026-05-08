import { redirect } from "next/navigation";

/**
 * /workspace cũ vô dụng cho sinh viên khiếm thị.
 * Voice mode `/` đã làm tất cả: upload, listen, ask, chat realtime.
 *
 * Code component vẫn còn ở git history để ai cần dev/debug có thể restore.
 */
export default function WorkspacePage() {
  redirect("/");
}

export const metadata = {
  title: "Đã chuyển hướng",
  robots: { index: false },
};
