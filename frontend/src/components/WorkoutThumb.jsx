import { isCustomEx } from '../lib/exercises.js'
import { mediaOf, cleanUrl } from '../lib/media-refs.js'
import { t } from '../lib/i18n.js'
import { youtubeLinks } from '../lib/youtube.js'
import { Thumb } from './Media.jsx'
import Icon from './Icon.jsx'

// Whether an exercise has anything for the workout's media slot to show: the dataset's animation
// for a built-in, its own photo, video or link for a custom one (CustomMedia.jsx).
export const hasWorkoutMedia = (ex, notes) => !!ex && (
  (isCustomEx(ex) ? !!(mediaOf(ex) || cleanUrl(ex.url)) : !!ex.gif) || youtubeLinks(notes).length > 0
)

// Workouts show a compact preview beside the title. Expansion opens a temporary viewer;
// it never turns subsequent exercises into large inline animations.
export default function WorkoutThumb({ ex, onExpand }) {
  return <button type="button" className="wthumb" aria-label={t('Expand')} title={t('Expand')} onClick={onExpand}>
    <Thumb ex={ex} />
    <span className="wthumb-x" aria-hidden="true"><Icon name="expand" /></span>
  </button>
}
