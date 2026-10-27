import { workoutFit } from './fit-export.js'

/** Explicit opt-in only, including for imported profiles without this preference. */
export const stravaSharesWeights = state => state?.stravaShareWeights === true

/** A manual Strava upload file; this preference never changes the saved workout. */
export const stravaWorkoutFit = (workout, state, options) => workoutFit(workout, {
  ...options,
  includeWeights: stravaSharesWeights(state),
})
