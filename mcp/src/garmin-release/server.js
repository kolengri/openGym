#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { prepareSchema, deploySchema, statusSchema, publicError } from './contract.js'
import { ReleaseService } from './service.js'

// This entrypoint deliberately imports no workout, database, pairing or API-client modules.
process.umask(0o077)
delete process.env.DEBUG
delete process.env.PWDEBUG
const service = new ReleaseService()
const server = new McpServer({ name: 'opengym-garmin-release', version: '0.1.0' })
for (const [name, description, schema, action, readOnly] of [
  ['garmin_release_status', 'Offline configuration and release journal status; does not open a browser or read workout data.', statusSchema, 'status', true],
  ['garmin_release_prepare', 'Validate and snapshot a versioned IQ from artifacts/garmin-release-mcp/inbox with app ID, beta version and SHA256 checks. No upload.', prepareSchema, 'prepare', false],
  ['garmin_release_deploy', 'Explicitly upload a prepared IQ update to the existing owner-only Garmin beta. Final submission agrees to Garmin terms: obtain user confirmation for this specific upload before setting confirmSubmissionTerms. Requires configured authenticated browser session. Ambiguous attempts block retries.', deploySchema, 'deploy', false]
]) {
  server.registerTool(name, {
    description, inputSchema: schema,
    annotations: { readOnlyHint: readOnly, destructiveHint: !readOnly, idempotentHint: action !== 'deploy', openWorldHint: action === 'deploy' }
  }, async input => {
    try {
      const result = await service[action](input)
      return { content: [{ type: 'text', text: JSON.stringify(result) }] }
    } catch (error) {
      return { isError: true, content: [{ type: 'text', text: JSON.stringify(publicError(error)) }] }
    }
  })
}
await server.connect(new StdioServerTransport())
