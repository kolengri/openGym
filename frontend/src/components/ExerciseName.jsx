import { exerciseNameFor } from '../lib/i18n.js'

// Only separate the canonical English suffix that the user's name preference emitted.
// Custom names, English-only names and hidden-English settings retain their exact label.
export function exerciseNameParts(ex, fallback = '') {
  const label = ex ? exerciseNameFor(ex) : fallback
  if (ex?.n) {
    for (const suffix of [' (' + ex.n + ')', ' \u2068(' + ex.n + ')\u2069']) {
      if (label.endsWith(suffix) && label !== ex.n) return { primary: label.slice(0, -suffix.length), secondary: ex.n }
    }
  }
  return { primary: label, secondary: null }
}

export default function ExerciseName({ ex, fallback, className = '' }) {
  const name = exerciseNameParts(ex, fallback)
  return <span className={'exercise-name-lines ' + className}>
    <span className="exercise-name-primary">{name.primary}</span>
    {name.secondary && <span className="exercise-name-secondary" lang="en" dir="ltr">{name.secondary}</span>}
  </span>
}
