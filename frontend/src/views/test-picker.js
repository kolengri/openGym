// DOM harness for the shared SelectRow sheet. Callers still drive the actual row and option.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { bindUI } from '../components/ui.jsx'

export function createPickerHarness() {
  let render, host, root
  const destroy = () => {
    if (root) act(() => root.unmount())
    host?.remove()
    root = host = null
  }
  bindUI({ getState: () => ({ openSheet: fn => { render = fn; return { close: () => {} } } }) })
  return {
    destroy,
    open(row) {
      destroy()
      render = null
      if (!row) throw new Error('Picker row was not rendered')
      act(() => row.click())
      if (!render) throw new Error('Picker row did not open a sheet')
      host = document.createElement('div')
      document.body.append(host)
      root = createRoot(host)
      act(() => root.render(render(() => {})))
      const options = () => [...host.querySelectorAll('button.lrow')]
      return {
        get labels() { return options().map(b => b.querySelector('.lrow-t').textContent) },
        get selected() { return options().find(b => b.querySelector('.lrow-k'))?.querySelector('.lrow-t').textContent },
        get text() { return host.textContent },
        textFor(label) { return options().find(b => b.querySelector('.lrow-t').textContent === label)?.textContent },
        choose(label) {
          const option = options().find(b => b.querySelector('.lrow-t').textContent === label)
          if (!option) throw new Error(`Picker option was not rendered: ${label}`)
          act(() => option.click())
          destroy()
        },
      }
    },
  }
}
