import { execFileSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, writeFileSync, readFileSync, rmSync, symlinkSync } from 'node:fs'
import path from 'node:path'
import { MANIFEST_ID, RELEASE_HOME } from '../src/garmin-release/contract.js'

export const VERSION = '0.1.0-beta.3'
export function iq({ id = MANIFEST_ID, version = VERSION, type = 'watch-app', xml, binary = true, extra = '', manifestPath = 'manifest.xml', entries = {}, encryption, programDirectory = false, programSymlink = false, compressionLevel = 1 } = {}) {
  const parent = path.join(RELEASE_HOME, 'tests/7z-fixtures')
  mkdirSync(parent, { recursive: true, mode: 0o700 })
  const temp = mkdtempSync(path.join(parent, 'fixture-'))
  try {
    const source = path.join(temp, 'source')
    mkdirSync(source, { mode: 0o700 })
    const files = {
      [manifestPath]: xml ?? `<iq:manifest xmlns:iq="http://www.garmin.com/xml/connectiq" version="3"><iq:application id="${id}" type="${type}"/>${extra}</iq:manifest>`,
      ...(binary && !programDirectory && !programSymlink ? { 'device/app.prg': Buffer.from(`Synthetic program fixture ${version}`) } : {}),
      ...entries
    }
    for (const [name, content] of Object.entries(files)) {
      const file = path.join(source, name)
      mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 })
      writeFileSync(file, content, { mode: 0o600 })
    }
    if (programDirectory || programSymlink) {
      mkdirSync(path.join(source, 'device'), { recursive: true, mode: 0o700 })
      if (programDirectory) mkdirSync(path.join(source, 'device/app.prg'), { mode: 0o700 })
      else symlinkSync('../manifest.xml', path.join(source, 'device/app.prg'))
    }
    const archive = path.join(temp, 'fixture.iq')
    const encrypt = encryption ? ['-pfixture-only-password', ...(encryption === 'headers' ? ['-mhe=on'] : [])] : []
    execFileSync(process.env.GARMIN_RELEASE_7ZZ || '/opt/homebrew/bin/7zz', ['a', '-t7z', `-mx=${compressionLevel}`, '-ms=off', '-snl', '-bd', '-bso0', '-bse2', ...encrypt, '--', archive, '.'], {
      cwd: source, input: '', timeout: 15000, maxBuffer: 64 * 1024
    })
    return readFileSync(archive)
  } finally { rmSync(temp, { recursive: true, force: true }) }
}
