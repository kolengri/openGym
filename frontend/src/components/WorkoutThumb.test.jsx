// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'
import { hasWorkoutMedia } from './WorkoutThumb.jsx'

describe('workout media availability', () => {
  const exercise = { id: 'no-animation', n: 'Exercise' }

  it('offers the compact viewer for a video provided only in program notes', () => {
    expect(hasWorkoutMedia(exercise, 'Technique https://youtu.be/dQw4w9WgXcQ')).toBe(true)
    expect(hasWorkoutMedia({ ...exercise, gif: 'exercise.gif' })).toBe(true)
  })

  it('does not offer media for ordinary notes or untrusted video URLs', () => {
    expect(hasWorkoutMedia(exercise, 'Keep your back straight')).toBe(false)
    expect(hasWorkoutMedia(exercise, 'https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ')).toBe(false)
    expect(hasWorkoutMedia(exercise, 'https://youtu.be/invalid')).toBe(false)
    expect(hasWorkoutMedia(null, 'https://youtu.be/dQw4w9WgXcQ')).toBe(false)
  })
})
