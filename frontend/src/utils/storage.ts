const KEY = "squad-builder:selectedPlayerIds";
const SUGGESTED_KEY = "squad-builder:suggestedPlayerIds";

export function loadSelectedIds(): number[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x) => Number.isInteger(x));
  } catch {
    return [];
  }
}

export function saveSelectedIds(ids: number[]) {
  localStorage.setItem(KEY, JSON.stringify(ids));
}

export function loadSuggestedIds(): number[] {
  try {
    const raw = localStorage.getItem(SUGGESTED_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x) => Number.isInteger(x));
  } catch {
    return [];
  }
}

export function saveSuggestedIds(ids: number[]) {
  localStorage.setItem(SUGGESTED_KEY, JSON.stringify(ids));
}
