export const TOUR_STORAGE_KEY = "afterdue_tour_seen";
export const TOUR_QUERY = "tour";
export const TOUR_SCENE_COUNT = 8;
export const TOUR_CHANGE_EVENT = "afterdue-tour-change";

function emitTourChange(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(TOUR_CHANGE_EVENT));
}

export function subscribeTour(onStoreChange: () => void): () => void {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(TOUR_CHANGE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(TOUR_CHANGE_EVENT, onStoreChange);
  };
}

export function tourSeen(): boolean {
  if (typeof window === "undefined") return true;
  try {
    return window.localStorage.getItem(TOUR_STORAGE_KEY) === "true";
  } catch {
    return true;
  }
}

export function markTourSeen(): void {
  try {
    window.localStorage.setItem(TOUR_STORAGE_KEY, "true");
  } catch {
    /* ignore quota / private mode */
  }
  emitTourChange();
}

export function clearTourSeen(): void {
  try {
    window.localStorage.removeItem(TOUR_STORAGE_KEY);
  } catch {
    /* ignore */
  }
  emitTourChange();
}
