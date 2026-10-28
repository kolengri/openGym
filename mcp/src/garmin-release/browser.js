import { APP_ID, isTargetUrl, fail, parseVersionLabel, versionLabelPattern } from './contract.js'

export class GarminBrowser {
  constructor(config, profileDir, chromium) {
    this.config = config
    this.profileDir = profileDir
    this.chromium = chromium
  }

  async open() {
    // Import lazily: stdio discovery and offline preparation need no installed browser.
    const chromium = this.chromium ?? (await import('playwright')).chromium
    this.context = await chromium.launchPersistentContext(this.profileDir, {
      headless: false, acceptDownloads: false, serviceWorkers: 'block',
      timeout: this.config.timeoutMs
    })
    this.context.setDefaultTimeout(this.config.timeoutMs)
    // No screenshots, tracing, HAR, console listeners, credentials or cookie export.
    this.page = await this.context.newPage()
    await this.page.goto(this.config.listingUrl, { waitUntil: 'domcontentloaded' })
  }

  async close() { await this.context?.close().catch(() => {}) }

  async guard(marker = this.config.ownerBeta, form = false) {
    if (!isTargetUrl(this.page.url())) fail('AUTH_HANDOFF', 'Open the session setup command to complete login, CAPTCHA or terms manually; verify the existing app URL.')
    for (const selector of this.config.handoffSelectors) {
      if (await this.page.locator(selector).isVisible()) fail('AUTH_HANDOFF', 'Complete login, CAPTCHA or terms manually using the session setup command.')
    }
    const locator = this.page.locator(marker.selector)
    await locator.waitFor({ state: 'visible' })
    const text = (await locator.textContent())?.trim()
    const matched = marker.prefix === true ? text?.startsWith(marker.text) : text === marker.text
    if (!matched) fail(form ? 'FORM_NOT_VERIFIED' : 'BETA_NOT_VERIFIED', form
      ? 'The existing app update form identity did not match.'
      : 'The existing owner-only beta marker did not match. No visibility setting was changed.')
  }

  async inspect() {
    await this.guard()
    const locator = this.page.locator(this.config.currentVersion)
    await locator.waitFor({ state: 'visible' })
    return { appId: APP_ID, ownerOnlyBeta: true, version: parseVersionLabel(await locator.textContent()) }
  }

  async deploy({ version, expectedCurrentVersion, releaseNotes, bytes, beforeUpload }) {
    try {
      await this.open()
      const current = await this.inspect()
      if (current.version !== expectedCurrentVersion) fail('REMOTE_VERSION_MISMATCH', 'The existing beta version differs from expectedCurrentVersion. Reconcile it before deployment.')
      if (this.config.updateButton) await this.page.locator(this.config.updateButton).click()
      await this.guard(this.config.formIdentity, true)
      const file = this.page.locator(this.config.fileInput)
      await file.waitFor({ state: 'attached' })
      // File selection can itself send the binary. Persist intent BEFORE this boundary.
      await beforeUpload()
      await file.setInputFiles({ name: `opengym-garmin-${version}.iq`, mimeType: 'application/octet-stream', buffer: bytes })
      await this.page.locator(this.config.versionInput).fill(version)
      if (this.config.nextButton) {
        await this.guard(this.config.formIdentity, true)
        await this.page.locator(this.config.nextButton).click()
      }
      await this.guard(this.config.formIdentity, true)
      await this.page.locator(this.config.releaseNotesInput).fill(releaseNotes)
      await this.page.locator(this.config.submitButton).click()
      const accepted = this.page.locator(this.config.uploadAccepted.selector)
      await accepted.waitFor({ state: 'visible' })
      if ((await accepted.textContent())?.trim() !== this.config.uploadAccepted.text) fail('UPLOAD_NOT_VERIFIED', 'Upload completion was not verified.')
      // A toast alone is insufficient. Re-read the existing listing's version and beta marker.
      await this.page.goto(this.config.listingUrl, { waitUntil: 'domcontentloaded' })
      const exactVersion = versionLabelPattern(version)
      await this.page.locator(this.config.currentVersion).filter({ hasText: exactVersion }).waitFor({ state: 'visible' })
      const result = await this.inspect()
      if (result.version !== version) fail('REMOTE_VERSION_MISMATCH', 'Updated beta version could not be verified.')
      return result
    } finally { await this.close() }
  }
}
