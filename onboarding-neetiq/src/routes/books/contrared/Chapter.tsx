import { useEffect, useRef } from 'react'
import ScrollSection from '../../../components/scroll/ScrollSection'
import TextReveal from '../../../components/scroll/TextReveal'
import BodyReveal from '../../../components/scroll/BodyReveal'
import CodeTyper from '../../../components/scroll/CodeTyper'
import CounterReveal from '../../../components/scroll/CounterReveal'
import SplitScreen from '../../../components/scroll/SplitScreen'
import DiagramDraw from '../../../components/scroll/DiagramDraw'
import ScanDivider from '../../../components/shell/ScanDivider'
import type { Chapter as ChapterData, Section } from '../../../lib/contentLoader'

interface ChapterProps {
  chapter: ChapterData
  onComplete: () => void
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function cfg(section: Section): any {
  return (section.visual?.config ?? {}) as any
}

function parseSplitContent(content: string) {
  const parts = content.split(/\.\s+(?=[A-Z])/)
  const mid = Math.ceil(parts.length / 2)
  return {
    left: parts.slice(0, mid).join('. '),
    right: parts.slice(mid).join('. '),
  }
}

function renderSection(section: Section, index: number) {
  switch (section.type) {
    case 'text':
      return (
        <ScrollSection key={index}>
          <BodyReveal>
            <p>{section.content}</p>
          </BodyReveal>
        </ScrollSection>
      )

    case 'code':
      return (
        <ScrollSection key={index}>
          <CodeTyper
            code={section.content}
            language={cfg(section).language as string | undefined}
          />
        </ScrollSection>
      )

    case 'counter': {
      const c = cfg(section)
      return (
        <ScrollSection key={index}>
          <div className="flex gap-12 flex-wrap">
            {c.target != null ? (
              <CounterReveal
                target={c.target as number}
                prefix={c.prefix as string | undefined}
                suffix={c.suffix as string | undefined}
              />
            ) : (
              <BodyReveal>
                <p>{section.content}</p>
              </BodyReveal>
            )}
          </div>
        </ScrollSection>
      )
    }

    case 'split-screen': {
      const visual = section.visual
      const c = cfg(section)
      if (visual?.type === 'comparison' && c.left && c.right) {
        const leftItems: string[] = c.left.items || []
        const rightItems: string[] = c.right.items || []
        return (
          <ScrollSection key={index}>
            <SplitScreen
              leftLabel={c.left.label || 'Option A'}
              rightLabel={c.right.label || 'Option B'}
              leftFade
              rightGlow
              left={
                <ul className="space-y-2">
                  {leftItems.map((item: string, i: number) => (
                    <li key={i} className="text-text-muted text-sm">{item}</li>
                  ))}
                </ul>
              }
              right={
                <ul className="space-y-2">
                  {rightItems.map((item: string, i: number) => (
                    <li key={i} className="text-text-primary text-sm">{item}</li>
                  ))}
                </ul>
              }
            />
          </ScrollSection>
        )
      }
      // Fallback: parse content string
      const { left, right } = parseSplitContent(section.content)
      return (
        <ScrollSection key={index}>
          <SplitScreen
            leftLabel="Before"
            rightLabel="After"
            leftFade
            rightGlow
            left={<p className="text-text-muted text-sm">{left}</p>}
            right={<p className="text-text-primary text-sm">{right}</p>}
          />
        </ScrollSection>
      )
    }

    case 'diagram': {
      const c = cfg(section)
      const layers: any[] = c.layers || []
      return (
        <ScrollSection key={index}>
          <DiagramDraw>
            <div className="bg-surface border border-border rounded-lg p-6">
              <p className="text-text-primary text-sm leading-relaxed">{section.content}</p>
              {layers.length > 0 && (
                <div className="mt-4 space-y-3">
                  {layers.map((layer: any, i: number) => (
                    <div key={i} className="flex items-start gap-3">
                      <span className="text-gold font-mono text-xs mt-0.5 shrink-0">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <div>
                        <span className="text-text-primary font-medium text-sm">
                          {layer.name}
                        </span>
                        {layer.detail && (
                          <span className="text-text-muted text-xs ml-2">{layer.detail}</span>
                        )}
                        {layer.nodes && (
                          <div className="flex gap-2 mt-1 flex-wrap">
                            {layer.nodes.map((node: string, j: number) => (
                              <span
                                key={j}
                                className="text-xs bg-surface-elevated border border-border rounded px-2 py-0.5 text-text-muted"
                              >
                                {node}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </DiagramDraw>
        </ScrollSection>
      )
    }

    case 'quote':
      return (
        <ScrollSection key={index}>
          <BodyReveal>
            <blockquote className="border-l-4 border-gold pl-6 py-2 italic text-text-primary font-serif text-lg leading-relaxed">
              {section.content}
            </blockquote>
          </BodyReveal>
        </ScrollSection>
      )

    default:
      return (
        <ScrollSection key={index}>
          <BodyReveal>
            <p>{section.content}</p>
          </BodyReveal>
        </ScrollSection>
      )
  }
}

export default function Chapter({ chapter, onComplete }: ChapterProps) {
  const endRef = useRef<HTMLDivElement>(null)
  const completedRef = useRef(false)

  useEffect(() => {
    if (!endRef.current) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !completedRef.current) {
          completedRef.current = true
          onComplete()
        }
      },
      { threshold: 0.5 }
    )

    observer.observe(endRef.current)
    return () => observer.disconnect()
  }, [onComplete])

  return (
    <div>
      <TextReveal as="h2">{chapter.title}</TextReveal>

      <div className="mt-8 space-y-6">
        {chapter.sections.map((section, index) => renderSection(section, index))}
      </div>

      {/* Sentinel for chapter completion tracking */}
      <div ref={endRef} className="h-4" />

      <ScanDivider className="my-10" />
    </div>
  )
}
