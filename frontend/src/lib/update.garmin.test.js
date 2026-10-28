import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
const h = vi.hoisted(() => ({ channel: 'garmin', packageName: 'ch.duartesantos.opengym.garmin.test', versionCode: 33 }))
vi.mock('./channel.js', () => ({ getChannel: async () => h.channel }))
vi.mock('@capacitor/core', () => ({ registerPlugin: () => ({ get: async () => ({ ...h }) }) }))
import { checkForUpdate, resetUpdateCheck } from './update.js'
const repo = 'https://github.com/kolengri/openGym/releases/download/'
function release(code, extra = {}) {
  const tag_name = `garmin-android-${code}`
  return { tag_name, name: `1.4.3-garmin.${code}`, draft: false, prerelease: false, assets: [`openGym-Garmin-${code}.apk`, `openGym-Garmin-${code}.apk.sha256`]
    .map(name => ({ name, browser_download_url: `${repo}${tag_name}/${name}` })), ...extra }
}
function feed(releases) { vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => releases }))) }
beforeEach(() => { resetUpdateCheck(); h.channel = 'garmin'; h.versionCode = 33; h.packageName = 'ch.duartesantos.opengym.garmin.test' })
afterEach(() => { vi.unstubAllGlobals() })
describe('Garmin fork updates', () => {
  it('uses only the owner fork and native build number, ignoring upstream and watch releases', async () => {
    feed([{ tag_name: 'v99.0.0' }, release(34), { tag_name: '0.1.0-beta.99' }, release(35), release(36, { prerelease: true }), release(37, { draft: true })])
    const result = await checkForUpdate()
    expect(fetch).toHaveBeenCalledWith('https://api.github.com/repos/kolengri/openGym/releases?per_page=100', expect.any(Object))
    expect(result).toMatchObject({ hasUpdate: true, latestVersion: '1.4.3-garmin.35', apkUrl: `${repo}garmin-android-35/openGym-Garmin-35.apk`, hashUrl: `${repo}garmin-android-35/openGym-Garmin-35.apk.sha256` })
    expect(result.releasesPage).toBe('https://github.com/kolengri/openGym/releases/tag/garmin-android-35')
  })
  it.each([[], [release(32)], [release(33)], [{ tag_name: 'garmin-android-033' }]].map(rows => ({ rows })))('does not offer equal, older or absent fork updates: $rows', async ({ rows }) => {
    feed(rows); expect((await checkForUpdate()).hasUpdate).toBe(false)
  })
  it.each(['missing-checksum', 'upstream-url', 'wrong-package-asset', 'duplicate-asset'])('refuses incomplete or untrusted release assets: %s', async kind => {
    const r = release(34)
    if (kind === 'missing-checksum') r.assets.pop()
    if (kind === 'upstream-url') r.assets[0].browser_download_url = r.assets[0].browser_download_url.replace('kolengri', 'DuarteSantos8')
    if (kind === 'wrong-package-asset') r.assets[0].name = 'openGym-34.apk'
    if (kind === 'duplicate-asset') r.assets.push(r.assets[0])
    feed([r]); await expect(checkForUpdate()).rejects.toThrow('Garmin APK and checksum')
  })
  it.each([null, 0, '33', 33.5])('fails closed if native version code is invalid: %j', async version => {
    h.versionCode = version; feed([release(34)])
    await expect(checkForUpdate()).rejects.toThrow('Invalid installed Garmin package identity')
    expect(fetch).not.toHaveBeenCalled()
  })
  it('refuses a different installed package before checking the network', async () => {
    h.packageName = 'ch.duartesantos.opengym'; feed([release(34)])
    await expect(checkForUpdate()).rejects.toThrow('Invalid installed Garmin package identity')
    expect(fetch).not.toHaveBeenCalled()
  })
  it('keeps errors retryable and rejects malformed API responses', async () => {
    feed({}); await expect(checkForUpdate()).rejects.toThrow('Invalid Garmin release list')
    feed([release(34)]); expect((await checkForUpdate()).hasUpdate).toBe(true)
  })
})
