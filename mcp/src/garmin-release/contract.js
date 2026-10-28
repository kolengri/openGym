import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { z } from 'zod'

export const APP_ID = '10ea70db-ee8f-4811-9b65-ec251468afae'
export const MANIFEST_ID = '6fcd6528636d4cc39c3ad1e317d7524a'
export const BASE_VERSION = '0.1.0-beta.2'
export const PROJECT_ROOT = fileURLToPath(new URL('../../../', import.meta.url))
export const RELEASE_HOME = path.join(PROJECT_ROOT, 'artifacts/garmin-release-mcp')
export const MAX_IQ_BYTES = 64 * 1024 * 1024
export const versionSchema = z.string().max(20).regex(/^(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})-beta\.(0|[1-9]\d{0,3})$/)
export const hashSchema = z.string().regex(/^[a-f0-9]{64}$/)
export const prepareSchema = z.object({ appId: z.literal(APP_ID), version: versionSchema, sha256: hashSchema }).strict()
export const deploySchema = prepareSchema.extend({
  expectedCurrentVersion: versionSchema,
  confirmOwnerOnlyBeta: z.literal(true),
  confirmSubmissionTerms: z.literal(true),
  releaseNotes: z.string().trim().min(1).max(2000)
}).strict()
export const statusSchema = z.object({ version: versionSchema.optional() }).strict()

const selector = z.string().min(1).max(500).refine(s => !/REPLACE_/i.test(s))
const marker = z.object({ selector, text: z.string().trim().min(1).max(200), prefix: z.boolean().optional() }).strict()
export const browserConfigSchema = z.object({
  schemaVersion: z.literal(1),
  reviewedForExistingOwnerBeta: z.literal(true),
  listingUrl: z.string().url().refine(isTargetUrl),
  ownerBeta: marker,
  currentVersion: selector,
  updateButton: selector.optional(),
  formIdentity: marker,
  fileInput: selector,
  versionInput: selector,
  nextButton: selector.optional(),
  releaseNotesInput: selector,
  submitButton: selector,
  uploadAccepted: marker,
  handoffSelectors: z.array(selector).min(1).max(10),
  timeoutMs: z.number().int().min(1000).max(120000).default(30000)
}).strict()

// Observed Store labels include either 'Version X' or 'X (Internal: N)'.
// Keep parsing anchored so unrelated dates or versions cannot satisfy the fence.
export function versionLabelPattern(version) {
  return new RegExp(`^(?:Version\\s+)?v?${version.replaceAll('.', '\\.')}\\s*(?:\\(Internal:\\s*\\d+\\))?\\s*$`)
}

export function parseVersionLabel(text) {
  const value = String(text ?? '').trim()
  const match = /^(?:Version\s+)?v?(\d{1,4}\.\d{1,4}\.\d{1,4}-beta\.\d{1,4})\s*(?:\(Internal:\s*\d+\))?\s*$/.exec(value)
  if (!match || !versionSchema.safeParse(match[1]).success) fail('REMOTE_VERSION_MISMATCH', 'The beta version label could not be read unambiguously.')
  return match[1]
}

export function isTargetUrl(value) {
  try {
    const u = new URL(value)
    return u.protocol === 'https:' && ['apps.garmin.com', 'apps-developer.garmin.com'].includes(u.hostname) &&
      !u.username && !u.password && !u.port && !u.search && !u.hash &&
      u.pathname.split('/').includes(APP_ID)
  } catch { return false }
}

export function newerThan(a, b) {
  const numbers = v => versionSchema.parse(v).split(/[.\-]/).filter(x => x !== 'beta').map(Number)
  const aa = numbers(a), bb = numbers(b)
  for (let i = 0; i < aa.length; i++) if (aa[i] !== bb[i]) return aa[i] > bb[i]
  return false
}

export class ReleaseError extends Error {
  constructor(code, message) { super(message); this.code = code }
}

export function fail(code, message) { throw new ReleaseError(code, message) }

// Third-party errors may include cookies, URLs, DOM text or local credential paths.
export function publicError(error) {
  return error instanceof ReleaseError
    ? { code: error.code, message: error.message }
    : { code: 'LOCAL_FAILURE', message: 'Local release operation failed. No raw diagnostic data is returned.' }
}

export function parse(schema, input) {
  const result = schema.safeParse(input)
  if (!result.success) fail('INVALID_INPUT', 'Input does not match the release contract.')
  return result.data
}
