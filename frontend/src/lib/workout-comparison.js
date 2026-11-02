import { lastEntryFor, modeOf } from './history.js'
import { entryDbLoad, historyAs } from './dumbbells.js'
import { isSideSet, isWarmupRow, modeForEntry } from './workout-model.js'

// Read in this entry's load meaning, from the history already scoped to the session's day.
export function previousWorkSets(history, entry) {
  const last = lastEntryFor(historyAs(history, entry.id, entryDbLoad(entry)), entry.id, entry.rid)
  const cfg = { ...entry.target, id: entry.id }
  return last && modeForEntry(last) === modeOf(cfg) ? last.sets : []
}

// Warm-ups never shift the work-set comparison. New sets have no invented reference;
// switching between combined and separate sides has no comparable per-row numbers either.
export function previousSetAt(entry, index, previous, side) {
  const row = entry.sets[index]
  if (!row || isWarmupRow(row)) return null
  const ordinal = entry.sets.slice(0, index + 1).filter(s => !isWarmupRow(s)).length - 1
  const prev = previous[ordinal]
  if (!prev || isSideSet(row) !== isSideSet(prev) || row.side !== prev.side) return null
  return side ? prev.sides?.[side] ?? null : prev
}
