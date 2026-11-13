type PrismModule = typeof import('prismjs')
let core: Promise<PrismModule> | undefined
const loaded = new Map<string, Promise<unknown>>()
const languages: Record<string, () => Promise<unknown>> = {
  python: () => import('prismjs/components/prism-python'),
  bash: () => import('prismjs/components/prism-bash'),
  json: () => import('prismjs/components/prism-json'),
  sql: () => import('prismjs/components/prism-sql'),
  yaml: () => import('prismjs/components/prism-yaml'),
  java: () => import('prismjs/components/prism-java'),
  docker: async () => {
    await loadLanguage('bash')
    return import('prismjs/components/prism-docker')
  },
  powershell: () => import('prismjs/components/prism-powershell'),
}

function loadLanguage(language: string): Promise<unknown> {
  if (!loaded.has(language)) loaded.set(language, languages[language]?.() ?? Promise.resolve())
  return loaded.get(language)!
}

export async function highlightCode(element: HTMLElement): Promise<void> {
  if ((element.textContent?.length ?? 0) > 50000 || !element.isConnected) return
  const language = element.className.match(/language-([\w-]+)/)?.[1] ?? ''
  const aliases: Record<string, string> = {
    py: 'python',
    shell: 'bash',
    sh: 'bash',
    yml: 'yaml',
    ps1: 'powershell',
  }
  const name = aliases[language] ?? language
  core ??= import('prismjs').then((module) => {
    const prism = 'default' in module ? (module.default as PrismModule) : module
    Object.assign(prism, { manual: true })
    return prism
  })
  const prism = await core
  if (name !== language) element.classList.replace(`language-${language}`, `language-${name}`)
  await loadLanguage(name)
  if (element.isConnected) prism.highlightElement(element)
}
