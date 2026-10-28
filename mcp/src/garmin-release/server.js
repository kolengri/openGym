#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { pathToFileURL } from 'node:url'
import { prepareSchema, deploySchema, statusSchema, publicError } from './contract.js'
import { ReleaseService } from './service.js'
import { ConfirmationMonitor } from './monitor.js'

// This entrypoint deliberately imports no workout, database, pairing or API-client modules.
process.umask(0o077)
delete process.env.DEBUG
delete process.env.PWDEBUG
export function createReleaseServer(service = new ReleaseService()) {
  const monitor = new ConfirmationMonitor(service)
  const server = new McpServer({ name: 'opengym-garmin-release', version: '0.3.0' })
  for (const [name, description, schema, action, readOnly] of [
    ['garmin_release_status', 'Offline configuration and release journal status; does not open a browser or read workout data.', statusSchema, 'status', true],
    ['garmin_release_check', 'Verify the authenticated owner beta through direct HTTP. Persist rotated session cookies and attempt normal SSO renewal; no browser control or upload.', statusSchema.pick({}), 'check', false],
    ['garmin_release_verify', 'GET-only final verification of the specific durable accepted beta submission, optionally selecting its version. May renew/persist the session and checkpoint confirmation. Never uploads or recovers ambiguous writes; deployment enable is not required.', statusSchema, 'verify', true],
    ['garmin_release_prepare', 'Validate and snapshot a versioned IQ from artifacts/garmin-release-mcp/inbox with app ID, beta version and SHA256 checks. No upload.', prepareSchema, 'prepare', false],
    ['garmin_release_deploy', 'Explicitly upload a prepared IQ update to the existing owner-only Garmin beta. Final submission agrees to Garmin terms: obtain user confirmation for this specific upload before setting confirmSubmissionTerms. Requires a verified private HTTP cookie session. Accepted submissions may return awaiting_confirmation for GET-only monitoring; ambiguous attempts block retries.', deploySchema, 'deploy', false]
  ]) {
    server.registerTool(name, {
      description, inputSchema: schema,
      annotations: { readOnlyHint: readOnly, destructiveHint: !readOnly, idempotentHint: action !== 'deploy', openWorldHint: ['deploy', 'check', 'verify'].includes(action) }
    }, async input => {
      try {
        const result = await service[action](input)
        if (['deploy', 'verify'].includes(action)) await monitor.start()
        return { content: [{ type: 'text', text: JSON.stringify(action === 'status' ? { ...result, monitor: monitor.status() } : result) }] }
      } catch (error) {
        return { isError: true, content: [{ type: 'text', text: JSON.stringify(publicError(error)) }] }
      }
    })
  }
  server.server.onclose = () => monitor.stop()
  return { server, monitor }
}

export async function runReleaseServer(service = new ReleaseService()) {
  const { server, monitor } = createReleaseServer(service)
  await server.connect(new StdioServerTransport())
  await monitor.start()
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) await runReleaseServer()
