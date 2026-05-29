import { forwardRef, useImperativeHandle, useRef } from 'react'

export interface EmojiOverlayHandle {
    addReaction: (player: string, emoji: string) => void
}

const EmojiOverlay = forwardRef<EmojiOverlayHandle>(function EmojiOverlay(_, ref) {
    const containerRef = useRef<HTMLDivElement>(null)

    useImperativeHandle(ref, () => ({
        addReaction(player: string, emoji: string) {
            const container = containerRef.current
            if (!container) return

            const x = Math.random() * 65 + 10

            const el = document.createElement('div')
            el.className = 'animate-emoji-float'
            el.style.cssText = `position:absolute;bottom:5rem;left:${x}%;display:flex;flex-direction:column;align-items:center;gap:2px;pointer-events:none;`

            const emojiSpan = document.createElement('span')
            emojiSpan.style.cssText = 'font-size:2.25rem;filter:drop-shadow(0 4px 6px rgba(0,0,0,.15));user-select:none;'
            emojiSpan.textContent = emoji

            const nameSpan = document.createElement('span')
            nameSpan.style.cssText = 'font-size:10px;color:#fff;background:rgba(0,0,0,.6);padding:1px 6px;border-radius:9999px;font-weight:700;white-space:nowrap;'
            nameSpan.textContent = player

            el.appendChild(emojiSpan)
            el.appendChild(nameSpan)
            container.appendChild(el)

            el.addEventListener('animationend', () => el.remove(), { once: true })
        },
    }))

    return <div ref={containerRef} className="fixed inset-0 pointer-events-none overflow-hidden z-[180]" />
})

export default EmojiOverlay
