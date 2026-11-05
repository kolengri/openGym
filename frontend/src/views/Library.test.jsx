// @vitest-environment happy-dom
// Favourites (issue #6): the Library floats starred exercises to the top of the current
// result list — after the search and body-part filters, without reordering the rest.
import React, { act } from 'react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Library from './Library.jsx'
import { EXDB } from '../lib/exercises.js'
import { useUI } from '../store/useUI.js'
import { CASED_NAME_LANGS, EXERCISE_NAME_LANGS, _setLangState } from '../lib/i18n-core.js'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const mocks = vi.hoisted(() => {
  const state = { S: null }
  state.snapshot = () => ({ S: state.S, user: null, update: mut => { const next = structuredClone(state.S); mut(next); state.S = next } })
  return state
})
vi.mock('../store/useStore.js', () => {
  const useStore = selector => selector ? selector(mocks.snapshot()) : mocks.snapshot()
  useStore.getState = mocks.snapshot
  return { useStore }
})
vi.mock('react-router-dom', () => ({ useNavigate: () => () => {} }))
vi.mock('../sheets.jsx', () => ({ exerciseDetailSheet: vi.fn(), addToRoutineSheet: vi.fn(), customExSheet: vi.fn() }))

const mounted = []
function render() {
  const host = document.createElement('div')
  document.body.appendChild(host)
  const root = createRoot(host)
  mounted.push(root)
  act(() => root.render(<Library />))
  return host
}
const names = host => [...host.querySelectorAll('.item-open .tt')].map(el => el.textContent)
const chooseBodyPart = (host, label) => {
  act(() => host.querySelector('.lib-search-filter').click())
  const sheet = useUI.getState().sheets.at(-1)
  const holder = document.createElement('div'); document.body.appendChild(holder)
  const root = createRoot(holder); mounted.push(root)
  act(() => root.render(sheet.render(() => {})))
  act(() => [...holder.querySelectorAll('.lib-body-parts button')].find(button => button.textContent === label).click())
}
const cssSource = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf8')

beforeEach(() => {
  mocks.S = { unit: 'kg', lang: 'en', routines: [], workouts: [], customEx: [], exWeights: {}, equipProfiles: [], activeEquipId: null, equipFilterOn: false }
  document.body.innerHTML = ''
})
afterEach(() => { act(() => { mounted.splice(0).forEach(root => root.unmount()) }) })

describe('Library favourites', () => {
  it('puts favourites first, marked with a star, and leaves the rest in catalogue order', () => {
    const plain = names(render())
    act(() => { mounted.splice(0).forEach(root => root.unmount()) })
    const fav = [plain[6], plain[2]]
    mocks.S.favEx = fav.map(n => EXDB.find(e => e.n === n).id)
    const host = render()
    const shown = names(host)
    expect(shown.slice(0, 2)).toEqual(plain.filter(n => fav.includes(n)))
    expect(shown.slice(2)).toEqual(plain.filter(n => !fav.includes(n)))
    const rows = [...host.querySelectorAll('.item')].filter(el => el.querySelector('.item-open'))
    expect(rows[0].querySelector('.fav-star')).not.toBeNull()
    expect(rows[2].querySelector('.fav-star')).toBeNull()
  })

  // The Library is the one page whose header puts a text button beside the title, so it leaves the
  // title the least room of anywhere in the app — 95px for Polish, 125px for Russian on a 320px
  // screen. The button must stay reachable (it is flex:none, the title block shrinks), but a title
  // squeezed that far must not come apart: at 34px "Упражнения" broke into three lines, so the
  // title drops a step on phone widths and breaks a word only as a last resort.
  it('keeps the header button reachable without shredding the title', () => {
    expect(cssSource).toContain('.hdr>div{min-width:0}')
    expect(cssSource).toContain('.hdr>.btn{flex:none}')
    // The compact approved title scale still preserves normal word wrapping.
    expect(cssSource).toMatch(/\.hdr h1\{font-size:var\(--fs-large\)/)
    expect(cssSource).toMatch(/--fs-large:1\.375rem/)
    const h1 = cssSource.match(/^\.hdr h1\{([^}]*)\}/m)
    expect(h1?.[1]).toContain('overflow-wrap:break-word')
    expect(h1[1]).not.toContain('overflow-wrap:anywhere')
    expect(h1[1]).not.toContain('hyphens:auto')
  })

  it('keeps a favourite on top inside a body-part filter, but never pulls one in from elsewhere', () => {
    const chest = EXDB.filter(e => e.bp === 'chest')
    const legs = EXDB.find(e => e.bp !== 'chest')
    mocks.S.favEx = [chest[4].id, legs.id]
    const host = render()
    chooseBodyPart(host, 'chest')
    const shown = names(host)
    expect(shown[0]).toBe(chest[4].n)
    expect(shown).not.toContain(legs.n)
  })
})

describe('Library browse tabs', () => {
  const choose = (host, label) => act(() => [...host.querySelectorAll('.lib-browse button')].find(b => b.textContent === label).click())
  const search = (host, value) => act(() => {
    const input = host.querySelector('.search input')
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })

  it('filters favourites and custom exercises while leaving stored preferences unchanged', () => {
    const own = { id: 'custom-press', n: 'My press', bp: 'chest', tg: 'pectorals', eq: 'dumbbell', custom: true }
    const legacy = { id: 'legacy-press', n: 'Legacy press', bp: 'chest', tg: 'pectorals', eq: '' }
    mocks.S.customEx = [own, legacy]
    mocks.S.favEx = [EXDB[0].id, own.id]
    const original = structuredClone(mocks.S)
    const host = render()
    choose(host, 'Favourites')
    expect(names(host)).toEqual([own.n, EXDB[0].n])
    expect(host.querySelectorAll('.fav-star')).toHaveLength(2)
    choose(host, 'My own')
    expect(names(host)).toEqual([own.n, legacy.n])
    choose(host, 'All')
    expect(names(host).length).toBe(40)
    expect(mocks.S).toEqual(original)
  })

  it('keeps search and body-part selection when switching tabs and scopes similar results', () => {
    const chest = EXDB.filter(e => e.bp === 'chest')
    const other = EXDB.find(e => e.bp !== 'chest')
    mocks.S.favEx = [chest[0].id, other.id]
    const host = render()
    chooseBodyPart(host, 'chest')
    choose(host, 'Favourites')
    expect(names(host)).toEqual([chest[0].n])
    search(host, chest[0].n + ' qwxz')
    expect(host.querySelector('.similar-label')).toBeTruthy()
    expect(names(host)).toEqual([chest[0].n])
    choose(host, 'All')
    expect(host.querySelector('.search input').value).toBe(chest[0].n + ' qwxz')
    expect(host.querySelector('.lib-filters button').textContent).toBe('chest')
  })

  it('shows an empty personal list without falling back to catalogue entries', () => {
    const host = render()
    choose(host, 'Favourites')
    expect(names(host)).toEqual([])
    expect(host.querySelector('.empty').textContent).toContain('No match')
    choose(host, 'My own')
    expect(names(host)).toEqual([])
    expect(host.querySelector('.hdr [data-tour="lib-new"]')).toBeTruthy()
  })
})

// #290 took the title-casing off every translated name; the packs stored lower-case then read
// lower-case down the whole list. Only German's own casing is left alone.
describe('Library exercise-name casing per language', () => {
  const packs = import.meta.glob('../exercise-names/*.js', { eager: true, import: 'default' })
  afterEach(() => _setLangState('en', {}, null, null))

  for (const lang of EXERCISE_NAME_LANGS) {
    it(`${lang}: every translated row is ${CASED_NAME_LANGS.includes(lang) ? 'left in its own casing' : 'title-cased'}`, () => {
      const pack = packs[`../exercise-names/${lang}.js`]
      _setLangState(lang, {}, null, pack)
      // Starred so they render on the first page: a partial pack may not cover the first rows.
      mocks.S.favEx = Object.keys(pack).slice(0, 3)
      const rows = [...render().querySelectorAll('.item-open .tt')]
      expect(rows.length).toBeGreaterThan(0)
      const translated = rows.filter(el => Object.values(pack).some(n => el.textContent.startsWith(n)))
      expect(translated.length, lang).toBeGreaterThan(0)
      for (const el of translated) expect(el.classList.contains('capitalize'), `${lang}: ${el.textContent}`).toBe(!CASED_NAME_LANGS.includes(lang))
    })
  }
})

// The header counts the catalogue, and from the first exercise of your own, those too (owner
// request for v1.3.10): "1324 animated exercises + 5 of your own". It has to stay one line on a
// phone, so it runs under the title row at full width, never wraps, and ellipsizes as a last resort.
describe('Library header count', () => {
  const sub = host => host.querySelector('.hdr .sub').textContent
  const own = n => Array.from({ length: n }, (_, i) => ({ id: 'c' + i, n: 'my move ' + i, bp: 'chest', eq: '', custom: true }))
  afterEach(() => _setLangState('en', {}, null, null))

  it('shows only the catalogue while you have no exercises of your own', () => {
    expect(sub(render())).toBe(`${EXDB.length} exercises with animations`)
  })

  it('adds "+ 1 of your own" for a single custom exercise', () => {
    mocks.S.customEx = own(1)
    expect(sub(render())).toBe(`${EXDB.length} animated exercises + 1 of your own`)
  })

  it('adds the count for several custom exercises', () => {
    mocks.S.customEx = own(5)
    expect(sub(render())).toBe(`${EXDB.length} animated exercises + 5 of your own`)
  })

  it('uses the language\'s own plural forms (Russian: 1 своё, 2 своих, 5 своих)', async () => {
    const { default: ru } = await import('../locales/ru.js')
    _setLangState('ru', ru, null, null)
    const forms = ru['{1} animated exercises + {0} of your own']
    expect(typeof forms).toBe('object')
    mocks.S.customEx = own(1)
    const one = sub(render())
    act(() => { mounted.splice(0).forEach(root => root.unmount()) })
    mocks.S.customEx = own(5)
    const five = sub(render())
    expect(one).toContain(String(EXDB.length))
    expect(five).toBe(forms.many.replace('{0}', '5').replace('{1}', String(EXDB.length)))
    expect(one).not.toBe(five.replace('5', '1'))
  })

  it('keeps the subtitle on one line on wider screens, clipping with an ellipsis', () => {
    expect(sub(render())).toBeTruthy()
    const rule = cssSource.match(/^\.hdr\.lib-hdr>\.sub\.lib-count\{([^}]*)\}/m)?.[1] || ''
    expect(rule).toContain('white-space:nowrap')
    expect(rule).toContain('overflow:hidden')
    expect(rule).toContain('text-overflow:ellipsis')
    expect(rule).toContain('flex:1 0 100%')
    expect(cssSource).toMatch(/^\.hdr\.lib-hdr\{[^}]*flex-wrap:wrap/m)
  })

  it('lets the subtitle wrap on narrow phones so nothing is cut at 320 px', () => {
    const narrow = cssSource.match(/@media \(max-width:360px\)\{\.hdr\.lib-hdr>\.sub\.lib-count\{([^}]*)\}\}/)?.[1] || ''
    expect(narrow).toContain('white-space:normal')
    expect(narrow).toContain('overflow:visible')
  })
})

describe('Library similar exercises', () => {
  const search = (host, text) => {
    const input = host.querySelector('.search input')
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
    act(() => { setter.call(input, text); input.dispatchEvent(new Event('input', { bubbles: true })) })
  }
  const label = host => host.querySelector('.similar-label')?.textContent || null

  it('offers what comes close instead of "No match" when nothing matches exactly', () => {
    const host = render()
    search(host, 'dumbbell curl qwxz')
    expect(label(host)).toBe('No exact match. These come close:')
    expect(host.textContent).not.toContain('No match')
    expect(names(host).slice(0, 5).some(n => /dumbbell.*curl/.test(n))).toBe(true)
  })

  it('lists similar ones under a short result list, without repeating a result', () => {
    const host = render()
    search(host, 'face pull')
    expect(label(host)).toBe('Similar exercises')
    const all = names(host)
    expect(new Set(all).size).toBe(all.length)
  })
})


describe('Library refinement actions and bilingual names', () => {
  afterEach(() => _setLangState('en', {}, null, null))

  it('puts creation in the header and offers the search text after an empty search', async () => {
    const { customExSheet } = await import('../sheets.jsx')
    const host = render()
    expect(host.querySelector('.list .ex-new')).toBeNull()
    expect(host.querySelector('.list [aria-label="Add to my plan"]')).toBeNull()
    expect(host.querySelector('.list .item .chev')).toBeTruthy()
    act(() => host.querySelector('.hdr [aria-label="Create your own exercise"]').click())
    expect(customExSheet).toHaveBeenLastCalledWith(null, expect.any(Function), '')
    const input = host.querySelector('.search input')
    act(() => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'qwxzqwxz')
      input.dispatchEvent(new Event('input', { bubbles: true }))
    })
    expect(host.querySelector('.list .ex-new')).toBeTruthy()
    act(() => host.querySelector('.list .ex-new').click())
    expect(customExSheet).toHaveBeenLastCalledWith(null, expect.any(Function), 'qwxzqwxz')
  })

  it('places only enabled English names on a separate isolated line', () => {
    const ex = EXDB[0]
    _setLangState('ru', {}, null, { [ex.id]: 'переведённое название' })
    let host = render()
    expect(host.querySelector('.item-open .tt').textContent).toBe('переведённое название')
    expect(host.querySelector('.lib-english').textContent).toBe(ex.n)
    expect(host.querySelector('.lib-english').getAttribute('dir')).toBe('ltr')
    act(() => mounted.splice(0).forEach(root => root.unmount()))
    _setLangState('ru', {}, null, { [ex.id]: 'переведённое название' }, true, true)
    host = render()
    expect(host.querySelector('.item-open .tt').textContent).toBe(ex.n)
    expect(host.querySelector('.lib-english')).toBeNull()
  })
})
