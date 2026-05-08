import { redirect } from "next/navigation";

/**
 * Pricing page paused — chỉ liên quan commercial, không phục vụ user khiếm thị trực tiếp.
 * Code và content vẫn còn ở git history.
 */
export default function PricingPage() {
  redirect("/");
}

export const metadata = {
  title: "Đã chuyển hướng",
  robots: { index: false },
};
