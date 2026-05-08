import { redirect } from "next/navigation";

/**
 * /tutor được hợp nhất vào / (voice landing) và /conversation.
 * Redirect về voice landing.
 */
export default function TutorPage() {
  redirect("/");
}

export const metadata = {
  title: "Đã chuyển hướng",
  robots: { index: false },
};
