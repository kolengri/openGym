import { constants } from 'node:fs'
import { open, lstat, mkdir, chmod, mkdtemp, writeFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import { XMLParser, XMLValidator } from 'fast-xml-parser'
import { MANIFEST_ID, MAX_IQ_BYTES, RELEASE_HOME, fail } from './contract.js'

export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex')

export async function directory(dir) {
  // Check each component: no writes through symlinked artifact/profile directories.
  for (let component = path.resolve(dir); ; component = path.dirname(component)) {
    try {
      const stat = await lstat(component)
      if (!stat.isDirectory() || stat.isSymbolicLink()) fail('UNSAFE_PATH', 'Release directories must be real directories.')
    } catch (e) { if (e.code !== 'ENOENT') throw e }
    if (path.dirname(component) === component) break
  }
  const parent = path.dirname(dir)
  if (parent !== dir) {
    try {
      const stat = await lstat(parent)
      if (!stat.isDirectory() || stat.isSymbolicLink()) fail('UNSAFE_PATH', 'Release directories must be real directories.')
    } catch (e) {
      if (e.code !== 'ENOENT') throw e
      await directory(parent)
    }
  }
  await mkdir(dir, { mode: 0o700 }).catch(e => { if (e.code !== 'EEXIST') throw e })
  const stat = await lstat(dir)
  if (!stat.isDirectory() || stat.isSymbolicLink()) fail('UNSAFE_PATH', 'Release directories must be real directories.')
  await chmod(dir, 0o700)
}

export async function readFileSafe(file, maxBytes = MAX_IQ_BYTES) {
  const handle = await open(file, constants.O_RDONLY | constants.O_NOFOLLOW)
  try {
    const stat = await handle.stat()
    if (!stat.isFile() || stat.size > maxBytes) fail('INVALID_FILE', 'Release file is missing, oversized, or not a regular file.')
    const bytes = Buffer.alloc(stat.size)
    let offset = 0
    while (offset < bytes.length) {
      const { bytesRead } = await handle.read(bytes, offset, bytes.length - offset, offset)
      if (!bytesRead) fail('FILE_CHANGED', 'Release file changed while reading.')
      offset += bytesRead
    }
    if ((await handle.stat()).size !== stat.size) fail('FILE_CHANGED', 'Release file changed while reading.')
    return bytes
  } finally { await handle.close() }
}

const MANIFEST_LIMIT = 1024 * 1024
const EXPANDED_LIMIT = 256 * 1024 * 1024
const ENTRY_LIMIT = 10000
const SEVEN_ZIP_MAGIC = Buffer.from('377abcaf271c', 'hex')

function sevenZip(args, maxOutput, capture = true) {
  const executable = process.env.GARMIN_RELEASE_7ZZ || '/opt/homebrew/bin/7zz'
  if (!path.isAbsolute(executable) || executable.includes('\0')) fail('ARCHIVE_TOOL_UNAVAILABLE', 'GARMIN_RELEASE_7ZZ must name an absolute trusted local 7zz executable.')
  return new Promise((resolve, reject) => {
    // No shell, stdin, passwords, wildcard/listfile expansion or raw diagnostics.
    const child = spawn(executable, args, { shell: false, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, LC_ALL: 'C' } })
    const chunks = []
    let outputBytes = 0, diagnosticBytes = 0, failure
    const abort = () => { failure = new Error('Archive process exceeded a bound'); child.kill('SIGKILL') }
    const timer = setTimeout(abort, 15000)
    child.stdout.on('data', chunk => {
      outputBytes += chunk.length
      if (outputBytes > maxOutput) abort()
      else if (capture && !failure) chunks.push(chunk)
    })
    child.stderr.on('data', chunk => { diagnosticBytes += chunk.length; if (diagnosticBytes > 64 * 1024) abort() })
    child.on('error', () => { clearTimeout(timer); reject(new Error('Archive executable unavailable')) })
    child.on('close', code => {
      clearTimeout(timer)
      if (failure || code !== 0 || diagnosticBytes) reject(new Error('Archive command failed'))
      else resolve({ bytes: outputBytes, output: capture ? Buffer.concat(chunks) : null })
    })
  })
}

function archiveEntries(listing) {
  const blocks = listing.trim().split(/\r?\n\r?\n/)
  if (blocks.length > ENTRY_LIMIT) throw new Error('Too many entries')
  const paths = new Set()
  let total = 0
  return blocks.map(block => {
    const fields = Object.create(null)
    for (const line of block.split(/\r?\n/)) {
      const separator = line.indexOf(' = ')
      if (separator < 1 || Object.hasOwn(fields, line.slice(0, separator))) throw new Error('Ambiguous entry metadata')
      fields[line.slice(0, separator)] = line.slice(separator + 3)
    }
    const name = fields.Path
    if (!name || /[\x00-\x1f\x7f\\]/.test(name) || path.posix.isAbsolute(name) || name.split('/').some(part => part === '..' || part === '.' || part === '') || paths.has(name)) throw new Error('Unsafe or duplicate entry path')
    paths.add(name)
    const size = /^\d+$/.test(fields.Size) ? Number(fields.Size) : NaN
    total += size
    if (!Number.isSafeInteger(size) || size < 0 || total > EXPANDED_LIMIT || fields.Encrypted === '+' || /7zAES/i.test(fields.Method ?? '')) throw new Error('Archive size or encryption is unsupported')
    const regular = fields.Folder !== '+' && !/^D|[dl]r[wx-]/.test(fields.Attributes ?? '') &&
      !Object.keys(fields).some(key => /link|stream/i.test(key)) && fields.Encrypted === '-' && /^[0-9A-F]{8}$/.test(fields.CRC ?? '')
    return { name, size, regular }
  })
}

async function manifestXml(bytes) {
  if (!bytes.subarray(0, SEVEN_ZIP_MAGIC.length).equals(SEVEN_ZIP_MAGIC)) throw new Error('IQ must be 7z')
  const parent = path.join(RELEASE_HOME, 'private', 'iq-validation')
  await directory(parent)
  const temp = await mkdtemp(path.join(parent, 'archive-'))
  try {
    const archive = path.join(temp, 'package.iq')
    await writeFile(archive, bytes, { flag: 'wx', mode: 0o600 })
    const common = ['-bd', '-bb0', '-bse2', '-bsp0', '-sccUTF-8', '-ssc', '-t7z', '-mmt=1', '-mmemuse=256m']
    const listed = await sevenZip(['l', '-slt', '-ba', ...common, '--', archive], 8 * 1024 * 1024)
    const entries = archiveEntries(listed.output.toString('utf8'))
    const manifest = entries.find(entry => entry.name === 'manifest.xml')
    const programs = entries.filter(entry => entry.name.endsWith('.prg'))
    if (!manifest?.regular || !manifest.size || manifest.size > MANIFEST_LIMIT || !programs.length || programs.some(entry => !entry.regular || !entry.size)) throw new Error('Missing regular manifest or program')
    // Read exactly named members to stdout. Never extract paths, keys or signatures to disk.
    const extract = ['x', '-so', '-bso0', '-spd', ...common, '--', archive]
    const xml = await sevenZip([...extract, 'manifest.xml'], MANIFEST_LIMIT)
    if (xml.bytes !== manifest.size) throw new Error('Manifest size differs from listing')
    const programSize = programs.reduce((sum, entry) => sum + entry.size, 0)
    const checked = await sevenZip([...extract, ...programs.map(entry => entry.name)], programSize, false)
    if (checked.bytes !== programSize) throw new Error('Program bytes differ from listing')
    return { xml: xml.output.toString('utf8'), programEntries: programs.length }
  } finally { await rm(temp, { recursive: true, force: true }) }
}

export async function validateIq(bytes, version, expectedHash) {
  if (!Buffer.isBuffer(bytes) || bytes.length > MAX_IQ_BYTES) fail('INVALID_FILE', 'IQ must be a buffer within the 64 MiB archive limit.')
  if (sha256(bytes) !== expectedHash) fail('HASH_MISMATCH', 'IQ SHA256 does not match the requested artifact.')
  let app, programEntries
  try {
    const contents = await manifestXml(bytes)
    const { xml } = contents
    programEntries = contents.programEntries
    if (/<!DOCTYPE|<!ENTITY/i.test(xml) || XMLValidator.validate(xml) !== true) throw new Error('Invalid XML')
    const document = new XMLParser({ ignoreAttributes: false, removeNSPrefix: true, processEntities: false }).parse(xml)
    if (document.manifest?.['@_version'] !== '3') throw new Error('Unsupported manifest schema')
    app = document.manifest.application
    if (!app || Array.isArray(app)) throw new Error('Invalid application')
  } catch { fail('INVALID_IQ', 'IQ must be an unencrypted bounded 7z archive readable by local 7zz, with one regular root manifest.xml and intact nonempty .prg files; XML entities are forbidden.') }
  const id = String(app['@_id'] ?? '').replaceAll('-', '').toLowerCase()
  if (id !== MANIFEST_ID) fail('MANIFEST_MISMATCH', 'IQ manifest identifies a different watch app.')
  if (app['@_type'] !== 'watch-app') fail('MANIFEST_MISMATCH', 'IQ manifest must identify a watch app.')
  // SDK exports carry manifest schema version 3, not the Store release version.
  return { manifestId: MANIFEST_ID, version, versionSource: 'caller-assigned-store-metadata',
    sha256: expectedHash, bytes: bytes.length, archiveFormat: '7z', manifestSchemaVersion: '3',
    programEntries, signatureVerification: 'not-verified' }
}
