import { copyFile, mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

const [mode] = process.argv.slice(2)
const {
  RELEASE_TAG: tag, GITHUB_REPOSITORY: repository, PLATFORM: platform,
  RUNNER_TEMP: runnerTemp, TARGET: target, TAURI_UPDATER_PUBLIC_KEY: publicKey,
} = process.env
const desktop = new URL('../apps/desktop/', import.meta.url)
const { version } = JSON.parse(await readFile(new URL('src-tauri/tauri.conf.json', desktop), 'utf8'))
const formats = {
  'windows-x86_64': { directory: 'nsis', suffix: '-setup.exe' },
  'linux-x86_64': { directory: 'appimage', suffix: '.AppImage' },
}

function assetName(platform) {
  return `My-Simple-AI_${version}_${platform}${formats[platform].suffix}`
}

function signatureText(text) {
  const encoded = text.trim()
  if (!/^[a-zA-Z0-9+/]+={0,2}$/.test(encoded)) throw new Error('Неверный формат ключа или подписи Tauri')
  return encoded
}

function updateSignature(text) {
  const encoded = signatureText(text)
  const comment = Buffer.from(encoded, 'base64').toString('utf8').split(/\r?\n/)
    .find((line) => line.startsWith('trusted comment: '))
  if (!comment?.split('\t').includes(`version:${version}`)) {
    throw new Error(`Подпись не соответствует версии ${version}`)
  }
  return encoded
}

function releaseUrl() {
  if (!/^v\d+\.\d+\.\d+$/.test(tag ?? '') || tag !== `v${version}`) {
    throw new Error('Тег выпуска должен совпадать с версией в tauri.conf.json')
  }
  if (!/^[a-z\d_.-]+\/[a-z\d_.-]+$/i.test(repository ?? '')) {
    throw new Error('Нужен GITHUB_REPOSITORY в формате owner/repository')
  }
  return `https://github.com/${repository}/releases`
}

if (mode === 'prepare') {
  const url = releaseUrl()
  const config = {
    bundle: { createUpdaterArtifacts: true },
    plugins: {
      updater: {
        pubkey: signatureText(publicKey ?? ''),
        endpoints: [`${url}/latest/download/latest.json`],
        requireSignedVersion: true,
        windows: { installMode: 'passive' },
      },
    },
  }
  await writeFile(join(runnerTemp, 'tauri-release.json'), JSON.stringify(config))
} else if (mode === 'stage') {
  const format = formats[platform]
  if (!format || !target) throw new Error('Нужны PLATFORM и TARGET')
  const bundle = new URL(`src-tauri/target/${target}/release/bundle/${format.directory}/`, desktop)
  const packages = (await readdir(bundle)).filter((name) => name.endsWith(format.suffix))
  if (packages.length !== 1) throw new Error(`Ожидался один пакет для ${platform}`)
  const staging = new URL('release-packages/', desktop)
  await mkdir(staging, { recursive: true })
  const name = assetName(platform)
  await copyFile(new URL(packages[0], bundle), new URL(name, staging))
  if (tag) {
    const signature = updateSignature(await readFile(new URL(`${packages[0]}.sig`, bundle), 'utf8'))
    await writeFile(new URL(`${name}.sig`, staging), signature)
  }
} else if (mode === 'manifest') {
  const url = releaseUrl()
  const manifest = { version, platforms: {} }
  for (const platform of Object.keys(formats)) {
    const name = assetName(platform)
    const path = join('release-packages', platform, name)
    if ((await stat(path)).size === 0) throw new Error(`Пустой пакет для ${platform}`)
    const signature = updateSignature(await readFile(`${path}.sig`, 'utf8'))
    manifest.platforms[platform] = {
      signature,
      url: `${url}/download/${tag}/${name}`,
    }
  }
  await writeFile(join('release-packages', 'latest.json'), JSON.stringify(manifest, null, 2) + '\n')
} else {
  throw new Error('Команда должна быть prepare, stage или manifest')
}
