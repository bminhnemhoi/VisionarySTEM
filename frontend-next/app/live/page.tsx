import { redirect } from "next/navigation";

/**
 * Camera Live page is paused — không phù hợp cho sinh viên khiếm thị.
 * Code component vẫn còn ở components/camera/ để future use.
 * Redirect mọi truy cập về voice landing.
 */
export default function LivePage() {
  redirect("/");
}

export const metadata = {
  title: "Đã chuyển hướng",
  robots: { index: false },
};
