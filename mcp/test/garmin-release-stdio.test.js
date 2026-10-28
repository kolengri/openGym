import { expect, it } from 'vitest'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { fileURLToPath } from 'node:url'
import { APP_ID } from '../src/garmin-release/contract.js'

it('discovers only release tools under real Node stdio and returns offline status', async () => {
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [fileURLToPath(new URL('../src/garmin-release/server.js', import.meta.url))],
    env: { PATH: process.env.PATH, OPENGYM_DATA: '/nonexistent/private-data-must-never-be-read' },
    stderr: 'pipe'
  })
  let stderr = ''
  transport.stderr?.on('data', bytes => { stderr += bytes.toString() })
  const client = new Client({ name: 'release-stdio-check', version: '1.0.0' })
  try {
    await client.connect(transport)
    const list = await client.listTools()
    expect(list.tools.map(t => t.name).sort()).toEqual(['garmin_release_deploy', 'garmin_release_prepare', 'garmin_release_status'])
    const result = await client.callTool({ name: 'garmin_release_status', arguments: {} })
    expect(JSON.parse(result.content[0].text)).toMatchObject({ appId: APP_ID, deploymentEnabled: false })
    const disabled = await client.callTool({ name: 'garmin_release_deploy', arguments: { appId: APP_ID, version: '0.1.0-beta.3', sha256: '0'.repeat(64), expectedCurrentVersion: '0.1.0-beta.2', confirmOwnerOnlyBeta: true, confirmSubmissionTerms: true, releaseNotes: 'Synthetic test only' } })
    expect(disabled.isError).toBe(true)
    expect(JSON.parse(disabled.content[0].text)).toMatchObject({ code: 'DEPLOY_DISABLED' })
    expect(stderr).toBe('')
  } finally { await client.close() }
}, 15000)
