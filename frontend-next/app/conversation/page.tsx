import { redirect } from "next/navigation";

/**
 * /conversation đã redundant — voice landing / cũng làm cùng việc + zero-click.
 * Redirect về voice landing để tránh confuse.
 */
export default function ConversationPage() {
  redirect("/");
}

export const metadata = {
  title: "Đã chuyển hướng",
  robots: { index: false },
};
