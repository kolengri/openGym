#!/usr/bin/env node
import { createInterface } from 'node:readline/promises'
import { stdin, stderr } from 'node:process'
import path from 'node:path'
import { ReleaseService } from '../src/garmin-release/service.js'
import { APP_ID, versionSchema, publicError, fail } from '../src/garmin-release/contract.js'
import { directory } from '../src/garmin-release/artifact.js'
import { GarminBrowser } from '../src/garmin-release/browser.js'

process.umask(0o077)
delete process.env.DEBUG
delete process.env.PWDEBUG
const service = new ReleaseService()
try {
  if (!stdin.isTTY) fail('INTERACTIVE_REQUIRED', 'Session setup requires a local interactive terminal.')
  await service.exclusive(async () => {
    const config = await service.config()
    await directory(service.profileDir)
    const browser = new GarminBrowser(config, service.profileDir)
    const prompt = createInterface({ input: stdin, output: stderr })
    try {
      await browser.open()
      await prompt.question('Complete Garmin login, MFA, CAPTCHA and any terms yourself. Return to the configured EXISTING owner-only beta listing, then press Enter. No upload will be performed. ')
      const evidence = await browser.inspect()
      if (!versionSchema.safeParse(evidence.version).success) fail('REMOTE_VERSION_MISMATCH', 'The configured listing version selector must return a beta version only.')
      await service.writeJson(path.join(service.privateDir, 'session-ready.json'), { appId: APP_ID, verifiedAt: new Date().toISOString() })
      stderr.write('Existing owner-only beta session verified locally. Browser closed; private profile retained.\n')
    } finally { prompt.close(); await browser.close() }
  })
} catch (error) { stderr.write(JSON.stringify(publicError(error)) + '\n'); process.exitCode = 1 }
