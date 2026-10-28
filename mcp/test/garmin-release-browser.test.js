import { describe, expect, it, vi } from 'vitest'
import { GarminBrowser } from '../src/garmin-release/browser.js'
import { APP_ID, BASE_VERSION, parseVersionLabel, versionLabelPattern } from '../src/garmin-release/contract.js'
import { VERSION, config } from './garmin-release-fixture.js'

function fixture({ current = BASE_VERSION, beta = config.ownerBeta.text, location = config.listingUrl, failAt, handoff = false } = {}) {
  const events = []
  let remoteVersion = current
  const page = {
    goto: vi.fn(async () => {}), url: () => location,
    locator: selector => ({
      isVisible: async () => handoff && selector === '#captcha',
      waitFor: async () => { if (failAt === 'wait') throw new Error('timeout with private DOM'); events.push(['wait', selector]) },
      textContent: async () => selector === '#owner-beta' ? beta : selector === '#form-beta' ? config.formIdentity.text : selector === '#accepted' ? config.uploadAccepted.text : remoteVersion,
      click: async () => { events.push(['click', selector]); if (failAt === selector) throw new Error('private failure'); if (selector === '#save-beta') remoteVersion = VERSION },
      fill: async value => { events.push(['fill', selector, value]) },
      setInputFiles: async file => { events.push(['file', file]); if (failAt === 'file') throw new Error('upload timeout') },
      filter: () => ({ waitFor: async () => { if (failAt === 'confirmation') throw new Error('confirmation timeout') } })
    })
  }
  const context = { newPage: async () => page, setDefaultTimeout: vi.fn(), close: vi.fn(async () => {}) }
  const chromium = { launchPersistentContext: vi.fn(async () => context) }
  const browser = new GarminBrowser(config, '/synthetic/private/profile', chromium)
  const args = { version: VERSION, expectedCurrentVersion: BASE_VERSION, releaseNotes: 'Beta fixes', bytes: Buffer.from('synthetic IQ'),
    beforeUpload: vi.fn(async () => { events.push(['intent']) }) }
  return { browser, chromium, context, page, args, events }
}

describe('configured browser adapter without Garmin access', () => {
  it.each([BASE_VERSION, `Version ${BASE_VERSION}`, `${BASE_VERSION} (Internal: 2)`, `v${BASE_VERSION}`])('reads the observed version label %s', async label => {
    expect(parseVersionLabel(label)).toBe(BASE_VERSION)
    expect(versionLabelPattern(BASE_VERSION).test(label)).toBe(true)
    const f = fixture({ current: label })
    expect(await f.browser.deploy(f.args)).toMatchObject({ version: VERSION, ownerOnlyBeta: true })
  })
  it.each(['Version 0.1.0-beta.20', 'Latest: 0.1.0-beta.2 and 0.1.0-beta.3', '0.1.0-beta.2 published', '0.1.0'])('does not accept a different or ambiguous version label %s', label => {
    expect(versionLabelPattern(BASE_VERSION).test(label)).toBe(false)
    if (label !== 'Version 0.1.0-beta.20') expect(() => parseVersionLabel(label)).toThrow()
  })
  it('uploads the validated buffer, fills version and notes, and verifies existing beta', async () => {
    const f = fixture()
    expect(await f.browser.deploy(f.args)).toEqual({ appId: APP_ID, version: VERSION, ownerOnlyBeta: true })
    const actionEvents = f.events.filter(x => x[0] !== 'wait')
    expect(actionEvents.map(x => x.slice(0, 2))).toEqual([
      ['click', '#update'], ['intent'], ['file', expect.objectContaining({ name: `opengym-garmin-${VERSION}.iq`, buffer: f.args.bytes })],
      ['fill', '#version'], ['click', '#next'], ['fill', '#notes'], ['click', '#save-beta']
    ])
    expect(f.chromium.launchPersistentContext).toHaveBeenCalledWith('/synthetic/private/profile', expect.objectContaining({ headless: false, acceptDownloads: false }))
    expect(f.context.close).toHaveBeenCalledOnce()
    expect(f.page.goto).toHaveBeenNthCalledWith(2, config.listingUrl, expect.any(Object))
  })
  it.each([
    [{ current: VERSION }, 'REMOTE_VERSION_MISMATCH'],
    [{ beta: 'Published' }, 'BETA_NOT_VERIFIED'],
    [{ location: 'https://sso.garmin.com/login' }, 'AUTH_HANDOFF'],
    [{ handoff: true }, 'AUTH_HANDOFF']
  ])('blocks preflight %j before file selection', async (options, code) => {
    const f = fixture(options)
    await expect(f.browser.deploy(f.args)).rejects.toMatchObject({ code })
    expect(f.args.beforeUpload).not.toHaveBeenCalled()
    expect(f.events.find(x => x[0] === 'file')).toBeUndefined()
    expect(f.context.close).toHaveBeenCalledOnce()
  })
  it.each(['file', '#next', '#save-beta', 'confirmation'])('propagates %s failure after durable intent, without a browser retry', async failAt => {
    const f = fixture({ failAt })
    await expect(f.browser.deploy(f.args)).rejects.toThrow()
    expect(f.args.beforeUpload).toHaveBeenCalledOnce()
    expect(f.events.filter(x => x[0] === 'file')).toHaveLength(1)
    expect(f.context.close).toHaveBeenCalledOnce()
  })
})
