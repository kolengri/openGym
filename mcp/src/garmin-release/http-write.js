import { request as httpsRequest } from 'node:https'
import { Readable } from 'node:stream'

// Fetch can replay a POST/PUT after HTTP 421, even with redirect:'manual'.
// Use one ClientRequest and a fresh connection; no redirect or retry machinery.
export async function writeOnce(url, { method, body, headers, signal }, { requestImpl = httpsRequest } = {}) {
  // Use the platform encoder for multipart boundaries/filenames and UTF-8 JSON.
  // IQ size has already been bounded and validated before reaching this function.
  const encoded = new Response(body, { headers })
  const bytes = Buffer.from(await encoded.arrayBuffer())
  return new Promise((resolve, reject) => {
    const request = requestImpl(url, {
      method, signal, agent: false,
      headers: { ...Object.fromEntries(encoded.headers), 'content-length': String(bytes.length) }
    }, incoming => {
      const responseHeaders = new Headers()
      for (let i = 0; i < incoming.rawHeaders.length; i += 2) responseHeaders.append(incoming.rawHeaders[i], incoming.rawHeaders[i + 1])
      resolve({ status: incoming.statusCode, headers: responseHeaders, body: Readable.toWeb(incoming) })
    })
    request.on('error', reject)
    request.end(bytes)
  })
}
