import { afterEach, describe, expect, it, vi } from 'vitest'
import { Agent, request as httpsRequest } from 'node:https'
import { Duplex } from 'node:stream'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { writeOnce } from '../src/garmin-release/http-write.js'
import { GarminApi, GarminSession } from '../src/garmin-release/api.js'
import { ReleaseService } from '../src/garmin-release/service.js'
import { APP_ID, MANIFEST_ID, RELEASE_HOME, BASE_VERSION } from '../src/garmin-release/contract.js'
import { directory, sha256 } from '../src/garmin-release/artifact.js'
import { iq, VERSION } from './garmin-release-fixture.js'

const homes = [], agents = []
afterEach(async () => {
  for (const agent of agents.splice(0)) agent.destroy()
  for (const home of homes.splice(0)) await rm(home, { recursive: true, force: true })
})

// Run the real node:https ClientRequest and HTTP parser over an in-memory Duplex.
// No DNS/TCP/TLS sockets are opened. Count bytes at the wire boundary, not fetch calls.
function wireTransport(handler) {
  const requests = [], options = []
  const agent = new Agent({ keepAlive: false })
  agents.push(agent)
  agent.createConnection = () => {
    let received = Buffer.alloc(0), replied = false
    return new Duplex({
      read() {},
      write(chunk, encoding, done) {
        received = Buffer.concat([received, chunk]); done()
        const end = received.indexOf('\r\n\r\n')
        if (end < 0 || replied) return
        const lines = received.subarray(0, end).toString().split('\r\n')
        const [method, target] = lines.shift().split(' ')
        const headers = Object.fromEntries(lines.map(line => { const i = line.indexOf(':'); return [line.slice(0, i).toLowerCase(), line.slice(i + 1).trim()] }))
        const length = Number(headers['content-length'])
        if (received.length < end + 4 + length) return
        replied = true
        const request = { method, target, headers, body: received.subarray(end + 4) }
        requests.push(request)
        Promise.resolve().then(() => handler(request)).then(reply => {
          if (reply.drop) { this.destroy(); return }
          const body = Buffer.from(reply.body ?? '')
          const headers = Object.entries({ 'Content-Length': String(body.length), Connection: 'close', ...reply.headers }).map(([name, value]) => `${name}: ${value}\r\n`).join('')
          this.push(`HTTP/1.1 ${reply.status ?? 200} Result\r\n${headers}\r\n`)
          this.push(body); this.push(null)
        }).catch(error => this.destroy(error))
      }
    })
  }
  const send = (url, init) => writeOnce(url, init, { requestImpl: (url, init, callback) => {
    options.push(init)
    expect(init.agent).toBe(false)
    // The sole injected boundary: replace the physical connection, not the client.
    return httpsRequest(url, { ...init, agent }, callback)
  } })
  return { send, requests, options }
}

async function bodyText(response) { return new Response(response.body).text() }
const signedInfo = version => ({ manifestAppId: MANIFEST_ID, signatureCheckSuccessFul: true, appType: 'Device App', newAppVersion: version })

async function releaseFixture(failureTarget, kind) {
  await directory(path.join(RELEASE_HOME, 'tests'))
  const home = await mkdtemp(path.join(RELEASE_HOME, 'tests/wire-'))
  homes.push(home)
  let remoteVersion = BASE_VERSION
  const metadata = { betaApp: true, shadowApp: false, localizedAppModel: [{ appLocale: 'en', appWhatsNew: 'old notes' }] }
  const fetchGet = vi.fn(async url => {
    const u = new URL(url)
    if (u.pathname.endsWith('/developers')) return Response.json({ userId: 'wire-fixture-owner', developer: true })
    if (u.pathname.includes('/appsLibraryExternalServices/')) return Response.json({ id: APP_ID, developerId: 'wire-fixture-owner', betaApp: true, latestExternalVersion: remoteVersion })
    if (u.pathname.endsWith('/metadata')) return Response.json({ ...metadata, appIqFileInfoResult: signedInfo(remoteVersion) })
    throw new Error('Unexpected GET')
  })
  const wire = wireTransport(async request => {
    const target = request.target.includes('/validate?') ? 'validation' : request.target.includes('/version?') ? 'publication' : 'metadata'
    if (target === failureTarget) return kind === 'drop' ? { drop: true } : { status: 421, body: 'Misdirected' }
    if (target === 'validation') return { body: JSON.stringify({ tempFileId: 'wire-temporary-id', iqFileInfoResult: signedInfo(VERSION) }) }
    if (target === 'publication') { remoteVersion = JSON.parse(request.body.toString()).appVersion; return {} }
    const form = await new Response(request.body, { headers: request.headers }).formData()
    Object.assign(metadata, JSON.parse(await form.get('appMetadata').text()))
    return {}
  })
  const apiFactory = file => new GarminApi(file, { fetchImpl: fetchGet, writeImpl: wire.send })
  const service = new ReleaseService({ home, enabled: true, apiFactory })
  await service.init()
  await new GarminSession(service.sessionFile).import([{ name: 'session', value: 'wire-fixture-only', domain: 'apps.garmin.com', path: '/', secure: true, httpOnly: true, expires: -1 }])
  await service.writeJson(path.join(service.privateDir, 'session-ready.json'), { appId: APP_ID })
  const bytes = iq(), hash = sha256(bytes)
  await writeFile(path.join(home, 'inbox', `opengym-garmin-${VERSION}.iq`), bytes)
  const prepare = { appId: APP_ID, version: VERSION, sha256: hash }
  await service.prepare(prepare)
  const deployment = { ...prepare, expectedCurrentVersion: BASE_VERSION, confirmOwnerOnlyBeta: true, confirmSubmissionTerms: true, releaseNotes: 'Single dispatch regression' }
  return { service, apiFactory, home, wire, deployment }
}

describe('single-dispatch HTTPS write transport', () => {
  it.each(['json', 'binary', 'metadata'])('surfaces 421 without replay for %s body encoding', async kind => {
    const wire = wireTransport(() => ({ status: 421, headers: { 'Set-Cookie': 'session=wire-rotation; Secure; HttpOnly; Path=/' }, body: 'first response' }))
    let body, headers = {}
    if (kind === 'json') { body = JSON.stringify({ tempFileId: 'fixture', appVersion: VERSION }); headers['Content-Type'] = 'application/json' }
    else {
      body = new FormData()
      body.append(kind === 'binary' ? 'appBinaryFile' : 'appMetadata', new Blob([kind === 'binary' ? Buffer.from([0, 255, 13, 10]) : '{"appTitle":"Зал"}'], { type: 'application/json' }), kind === 'binary' ? 'app.iq' : 'blob')
    }
    const r = await wire.send('https://apps.garmin.com/fixed', { method: kind === 'metadata' ? 'PUT' : 'POST', body, headers, signal: AbortSignal.timeout(2000) })
    expect(r.status).toBe(421)
    expect(await bodyText(r)).toBe('first response')
    expect(r.headers.getSetCookie()).toEqual(['session=wire-rotation; Secure; HttpOnly; Path=/'])
    expect(wire.requests).toHaveLength(1)
    const sent = wire.requests[0]
    expect(Number(sent.headers['content-length'])).toBe(sent.body.length)
    if (kind === 'json') expect(sent.body.toString()).toBe(body)
    else {
      const decoded = await new Response(sent.body, { headers: sent.headers }).formData()
      const blob = decoded.get(kind === 'binary' ? 'appBinaryFile' : 'appMetadata')
      expect(Buffer.from(await blob.arrayBuffer())).toEqual(kind === 'binary' ? Buffer.from([0, 255, 13, 10]) : Buffer.from('{"appTitle":"Зал"}'))
    }
  })
  it('does not follow write redirects', async () => {
    const wire = wireTransport(() => ({ status: 302, headers: { Location: 'https://elsewhere.test/' } }))
    const r = await wire.send('https://apps.garmin.com/fixed', { method: 'POST', body: '{}', headers: {}, signal: AbortSignal.timeout(2000) })
    expect(r.status).toBe(302)
    await bodyText(r)
    expect(wire.requests).toHaveLength(1)
  })
  it.each(['validation', 'publication', 'metadata'])('421 on %s is uncertain and blocks same/later versions after restart', async target => {
    const f = await releaseFixture(target, '421')
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'UPLOAD_UNCERTAIN' })
    const count = ['validation', 'publication', 'metadata'].indexOf(target) + 1
    expect(f.wire.requests).toHaveLength(count)
    const journal = await f.service.readJson(path.join(f.service.releaseDir(VERSION), 'journal.json'))
    expect(journal).toMatchObject({ state: 'uncertain', failureCode: 'GARMIN_HTTP_ERROR' })
    const restarted = new ReleaseService({ home: f.home, enabled: true, apiFactory: f.apiFactory })
    await expect(restarted.deploy(f.deployment)).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
    const version = '0.1.0-beta.4', bytes = iq({ version }), next = { appId: APP_ID, version, sha256: sha256(bytes) }
    await writeFile(path.join(f.home, 'inbox', `opengym-garmin-${version}.iq`), bytes)
    await restarted.prepare(next)
    await expect(restarted.deploy({ ...f.deployment, ...next })).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
    expect(f.wire.requests).toHaveLength(count)
  })
  it.each(['validation', 'publication', 'metadata'])('a dropped %s response is dispatched once and remains uncertain', async target => {
    const f = await releaseFixture(target, 'drop')
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'UPLOAD_UNCERTAIN' })
    expect(f.wire.requests).toHaveLength(['validation', 'publication', 'metadata'].indexOf(target) + 1)
    expect(await f.service.status()).toMatchObject({ unresolvedDeployment: { state: 'uncertain', version: VERSION } })
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
  })
  it('completes a verified deployment through real ClientRequests and returns the receipt on identical replay', async () => {
    const f = await releaseFixture(null)
    const result = await f.service.deploy(f.deployment)
    expect(result).toMatchObject({ state: 'deployed', version: VERSION })
    expect(f.wire.requests.map(x => x.method)).toEqual(['POST', 'POST', 'PUT'])
    expect(await f.service.deploy(f.deployment)).toEqual(result)
    expect(f.wire.requests).toHaveLength(3)
    expect((await readFile(f.service.sessionFile, 'utf8'))).toContain('wire-fixture-only')
  })
})
