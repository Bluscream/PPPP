const commander = require('commander')

commander
.version('1.0.0', '-v, --version')
.usage('[OPTIONS]...')
.option('-p, --port <value>', 'port number to use, default 3000', 3000)
.option('-t, --thisip <value>','IP of the interface to bind')
.option('-b, --broadcastip <value>','IP of the interface to bind','255.255.255.255')
.parse(process.argv);

const options = commander.opts()
console.log(options)
const PPPP = require('./pppp')

let p = null

function setupPPPP() {
  if (p) {
    console.log('pppp was already open, closing...')
    p.destroy()
    p = null
  }
  p = new PPPP(options)

  p.on('log', console.log)

  p.on('connected', (address, port) => {
    console.log(`Connected to camera at ${address}:${port}`)
    setTimeout(() => {
      p.sendCMDgetParams()
    }, 1000, p)
    // p.sendCMDGetDeviceFirmwareInfo()
    p.sendCMDrequestVideo1()
  })

  p.on('disconnected', (address, port) => {
    console.log(`Disconnected from camera at ${address}:${port}`)

  })

  p.on('videoFrame', (videoFrame) => {
    // console.log(videoFrame)
    let s = '--xxxxxxkkdkdkdkdkdk__BOUNDARY\r\n'
    s += 'Content-Type: image/jpeg\r\n\r\n'
    videoStream.write(Buffer.from(s))
    videoStream.write(videoFrame.frame)
  })

  p.on('cmd', console.log)
}

setupPPPP()


//http server with mjpeg
const PassThrough = require('stream').PassThrough
var videoStream = new PassThrough()

const http = require('http')
var url = require('url')
var path = require('path')
const querystring = require('querystring')
const server = http.createServer((req, res) => {
  if (req.url === '/favicon.ico') return
  console.log('[' + req.socket.remoteAddress + '] ' + req.method + ': ' + req.url)
  const purl = url.parse(req.url); // console.log(purl)
  const ppath = path.parse(purl.pathname); // console.log(ppath)
  const query  = querystring.parse(purl.query); //  console.log(query)
  if (req.url === '/') {
    res.statusCode = 200
    res.setHeader('Content-Type', 'text/html; charset=utf-8')
    res.end(
      '<!DOCTYPE html>\r\n<http><head></head><body><img src="/v.mjpg"></body></html>'
    )
  } else if (req.url === '/v.mjpg') {
    res.setHeader(
      'Content-Type',
      'multipart/x-mixed-replace; boundary="xxxxxxkkdkdkdkdkdk__BOUNDARY"'
    )
    videoStream.pipe(res)
  } else if (req.url === '/reconnect') {
    setupPPPP()
  } else if (purl.pathname.startsWith('/func/')) { // WARNING ⚠️ DO NOT USE THIS IN PRODUCTION
    let name = ppath.base
    let args = ""
    for (let e in query) {
      if (args.length > 0) {
        args += ','
      }
      args += e + "=" + query[e]
    }
    let eval_str = `p.${name}(${args})`
    let ret = eval(eval_str)
    res.statusCode = 200
    res.setHeader('Content-Type', 'application/json; charset=utf-8')
    res.end(JSON.stringify(ret))
  } else {
    res.statusCode = 404
    res.end()
  }
})

server.listen(options.port)

process.on('SIGINT', () => {
  server.close()
  server.unref()
  p.destroy()

  setTimeout(() => {
    console.log('exiting.')
    process.exit()
  }, 1000)
})
