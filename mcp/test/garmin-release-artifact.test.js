import { afterEach, describe, expect, it, vi } from 'vitest'
import path from 'node:path'
import { mkdtemp, writeFile, rm, access } from 'node:fs/promises'
import { BASE_VERSION, MAX_IQ_BYTES, RELEASE_HOME } from '../src/garmin-release/contract.js'
import { directory, sha256, validateIq } from '../src/garmin-release/artifact.js'
import { iq, VERSION } from './garmin-release-fixture.js'

const homes = []
afterEach(async () => {
  vi.unstubAllEnvs()
  for (const home of homes.splice(0)) await rm(home, { recursive: true, force: true })
})

const validate = bytes => validateIq(bytes, VERSION, sha256(bytes))

describe('SDK 7z IQ input contract', () => {
  it('assigns Store metadata without pretending the signed bytes contain that version', async () => {
    const bytes = iq({ version: BASE_VERSION }), before = sha256(bytes)
    const first = await validateIq(bytes, VERSION, before)
    const second = await validateIq(bytes, '0.1.0-beta.4', before)
    expect(first).toMatchObject({ version: VERSION, versionSource: 'caller-assigned-store-metadata',
      archiveFormat: '7z', manifestSchemaVersion: '3', signatureVerification: 'not-verified', programEntries: 1 })
    expect(second).toMatchObject({ version: '0.1.0-beta.4', sha256: before })
    expect(sha256(bytes)).toBe(before)
  })

  it.each([
    ['nested manifest', { manifestPath: 'nested/manifest.xml' }],
    ['empty program', { binary: false, entries: { 'device/app.prg': Buffer.alloc(0) } }],
    ['program directory', { programDirectory: true }],
    ['program symlink', { programSymlink: true }],
    ['oversized manifest', { xml: 'x'.repeat(1024 * 1024 + 1) }],
    ['encrypted payload', { encryption: 'data' }],
    ['encrypted header', { encryption: 'headers' }]
  ])('fails closed for %s without password input or broad extraction', async (_name, options) => {
    const bytes = iq(options)
    await expect(validate(bytes)).rejects.toMatchObject({ code: 'INVALID_IQ' })
  })

  it('rejects corrupt program bytes even when manifest and listing remain intact', async () => {
    const bytes = iq({ compressionLevel: 0 })
    const offset = bytes.indexOf(Buffer.from('Synthetic program fixture'))
    expect(offset).toBeGreaterThan(0)
    bytes[offset] ^= 1
    await expect(validate(bytes)).rejects.toMatchObject({ code: 'INVALID_IQ' })
  })

  it('bounds entry count before extracting members', async () => {
    const entries = Object.fromEntries(Array.from({ length: 10000 }, (_, i) => [`extra/${i}.txt`, '']))
    const bytes = iq({ entries })
    await expect(validate(bytes)).rejects.toMatchObject({ code: 'INVALID_IQ' })
  }, 15000)

  it('bounds the archive buffer and rejects ZIP rather than relying on synthetic ZIP fixtures', async () => {
    await expect(validateIq(Buffer.alloc(MAX_IQ_BYTES + 1), VERSION, '0'.repeat(64))).rejects.toMatchObject({ code: 'INVALID_FILE' })
    await expect(validate(Buffer.from('PK\x03\x04not-a-7z-IQ'))).rejects.toMatchObject({ code: 'INVALID_IQ' })
  })

  it('accepts an executable path only through trusted process configuration, never a shell command', async () => {
    const bytes = iq()
    await directory(path.join(RELEASE_HOME, 'tests'))
    const home = await mkdtemp(path.join(RELEASE_HOME, 'tests/command-boundary-'))
    homes.push(home)
    const marker = path.join(home, 'must-not-exist')
    vi.stubEnv('GARMIN_RELEASE_7ZZ', `/missing/7zz;touch ${marker}`)
    await expect(validate(bytes)).rejects.toMatchObject({ code: 'INVALID_IQ' })
    await expect(access(marker)).rejects.toMatchObject({ code: 'ENOENT' })
    vi.stubEnv('GARMIN_RELEASE_7ZZ', '7zz')
    await expect(validate(bytes)).rejects.toMatchObject({ code: 'INVALID_IQ' })
  })

  it('bounds subprocess output and returns no raw diagnostics', async () => {
    const bytes = iq()
    await directory(path.join(RELEASE_HOME, 'tests'))
    const home = await mkdtemp(path.join(RELEASE_HOME, 'tests/output-boundary-'))
    homes.push(home)
    const executable = path.join(home, 'oversized-output')
    await writeFile(executable, `#!${process.execPath}\nprocess.stdout.write(Buffer.alloc(9 * 1024 * 1024, 65))\n`, { mode: 0o700 })
    vi.stubEnv('GARMIN_RELEASE_7ZZ', executable)
    await expect(validate(bytes)).rejects.toMatchObject({ code: 'INVALID_IQ', message: expect.not.stringContaining(home) })
  })
})
