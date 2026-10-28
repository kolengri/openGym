#!/usr/bin/env node
import path from 'node:path'
import { lstat, unlink } from 'node:fs/promises'
import { randomUUID } from 'node:crypto'
import { stderr } from 'node:process'
import { ReleaseService } from '../src/garmin-release/service.js'
import { GarminApi, GarminSession } from '../src/garmin-release/api.js'
import { readFileSafe } from '../src/garmin-release/artifact.js'
import { APP_ID, publicError, fail } from '../src/garmin-release/contract.js'

process.umask(0o077)
const service = new ReleaseService()
try {
  const args = process.argv.slice(2)
  if (args.length && (args.length !== 2 || args[0] !== '--import' || !path.isAbsolute(args[1]))) fail('INVALID_INPUT', 'Usage: npm run garmin-release:session -- [--import /absolute/private/cookies.json]')
  let evidence
  if (args.length) {
    evidence = await service.exclusive(async () => {
      const stat = await lstat(args[1])
      if (!stat.isFile() || stat.isSymbolicLink() || (stat.mode & 0o077)) fail('PRIVATE_SESSION_REQUIRED', 'Cookie imports must be private regular files with mode 0600.')
      const data = JSON.parse((await readFileSafe(args[1], 256 * 1024)).toString('utf8'))
      // Verify a candidate without replacing the last working session on failure.
      const candidate = path.join(service.privateDir, `.session-import-${randomUUID()}.json`)
      try {
        await new GarminSession(candidate).import(Array.isArray(data) ? data : data.cookies)
        const verified = await new GarminApi(candidate).inspect()
        const session = JSON.parse((await readFileSafe(candidate, 256 * 1024)).toString('utf8'))
        await service.writeJson(service.sessionFile, session)
        await service.writeJson(path.join(service.privateDir, 'session-ready.json'), { appId: APP_ID, verifiedAt: new Date().toISOString() })
        return verified
      } finally { await unlink(candidate).catch(e => { if (e.code !== 'ENOENT') throw e }) }
    })
  }
  // No browser launch, password capture, cookie values or account details on stdout.
  evidence ??= await service.check()
  stderr.write(JSON.stringify(evidence) + '\n')
} catch (error) { stderr.write(JSON.stringify(publicError(error)) + '\n'); process.exitCode = 1 }
