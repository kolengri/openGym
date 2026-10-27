import { beforeEach, expect, it, vi } from 'vitest'
import { shareExport } from './mobile.js'

const bridge = vi.hoisted(() => ({ write: vi.fn(), share: vi.fn() }))
vi.mock('@capacitor/filesystem', () => ({ Directory: { Cache: 'CACHE' }, Encoding: { UTF8: 'UTF8' }, Filesystem: { writeFile: bridge.write } }))
vi.mock('@capacitor/share', () => ({ Share: { share: bridge.share } }))
beforeEach(() => { bridge.write.mockReset(); bridge.share.mockReset(); bridge.write.mockResolvedValue({ uri: 'private-cache' }) })

it('retains the existing export behavior without a guard', async () => {
  await shareExport('{}', 'synthetic.json')
  expect(bridge.share).toHaveBeenCalledWith({ title: 'synthetic.json', url: 'private-cache' })
})
it('does not open the native share sheet after cancellation while writing', async () => {
  let allowed = true
  bridge.write.mockImplementation(async () => { allowed = false; return { uri: 'private-cache' } })
  expect(await shareExport('{}', 'synthetic.json', { shouldShare: () => allowed })).toBe(false)
  expect(bridge.write).toHaveBeenCalledOnce()
  expect(bridge.share).not.toHaveBeenCalled()
})
it('checks cancellation after asynchronous plugin imports', async () => {
  let checks = 0
  await shareExport('{}', 'synthetic.json', { shouldShare: () => ++checks < 2 })
  expect(bridge.write).not.toHaveBeenCalled()
  expect(bridge.share).not.toHaveBeenCalled()
})
