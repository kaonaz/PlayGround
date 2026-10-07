#!/usr/bin/env node
// Minimal static file server for the built output (dist/). Foreground only.
import { createServer } from 'node:http'
import { readFileSync, statSync, existsSync } from 'node:fs'
import { resolve, join, extname } from 'node:path'

const root = resolve(process.argv[2] || 'dist')
const port = Number(process.env.PORT || 3000)
if (!existsSync(join(root, 'index.html'))) {
  console.error(`Static deployment output must contain index.html (missing in ${root}).`)
  process.exit(1)
}
const mime = {
  '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.webp': 'image/webp'
}
const server = createServer((req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost')
    const path = resolve(root, '.' + decodeURIComponent(url.pathname))
    if (path !== root && !path.startsWith(root + '/')) { res.writeHead(404); res.end(); return }
    let file = path
    try { if (statSync(path).isDirectory()) file = join(path, 'index.html') } catch { file = join(root, 'index.html') }
    if (!existsSync(file)) file = join(root, 'index.html')
    res.setHeader('Content-Type', mime[extname(file)] || 'application/octet-stream')
    res.setHeader('Cache-Control', 'no-cache')
    res.end(readFileSync(file))
  } catch { res.writeHead(404); res.end('Not found') }
})
server.listen(port, '0.0.0.0', () => console.log(`Serving ${root} on :${port}`))
