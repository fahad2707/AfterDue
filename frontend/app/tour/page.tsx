import { redirect } from "next/navigation";

/** Demo recording shortcut. Completing or skipping still writes afterdue_tour_seen. */
export default function TourPage() {
  redirect("/?tour=1");
}
