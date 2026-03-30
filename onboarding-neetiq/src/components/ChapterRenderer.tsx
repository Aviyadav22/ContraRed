import type { Chapter, Section, VisualConfig } from '../lib/contentLoader.ts'
import ScrollSection from './scroll/ScrollSection.tsx'
import BodyReveal from './scroll/BodyReveal.tsx'
import CodeTyper from './scroll/CodeTyper.tsx'
import CounterReveal from './scroll/CounterReveal.tsx'
import SplitScreen from './scroll/SplitScreen.tsx'
import TextReveal from './scroll/TextReveal.tsx'
import ScanDivider from './shell/ScanDivider.tsx'
import PipelineVisualizer from './visuals/PipelineVisualizer.tsx'
import ScoreCard from './visuals/ScoreCard.tsx'
import DeploymentMap from './visuals/DeploymentMap.tsx'
import ArchitectureDiagram from './visuals/ArchitectureDiagram.tsx'

/* ------------------------------------------------------------------ */
/*  Visual renderers (diagrams, grids, etc.)                          */
/* ------------------------------------------------------------------ */

function VisualGrid({ config }: { config: Record<string, unknown> }) {
  const items = (config.items ?? []) as Array<{ icon?: string; label: string; detail: string; value?: string }>
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
      {items.map((item, i) => (
        <div key={i} className="bg-surface border border-border rounded-lg p-4">
          <div className="text-gold font-mono text-xs uppercase tracking-widest mb-1">
            {item.value ?? item.label}
          </div>
          {item.value ? (
            <div className="text-text-muted text-sm">{item.label}</div>
          ) : (
            <div className="text-text-muted text-sm">{item.detail}</div>
          )}
        </div>
      ))}
    </div>
  )
}

function VisualFlow({ config }: { config: Record<string, unknown> }) {
  const nodes = (config.nodes ?? []) as string[]
  return (
    <div className="flex flex-col items-center gap-2 mt-4">
      {nodes.map((node, i) => (
        <div key={i} className="flex flex-col items-center">
          <div className="bg-surface border border-gold/30 rounded-lg px-4 py-2 text-text-primary text-sm font-mono text-center">
            {node}
          </div>
          {i < nodes.length - 1 && (
            <div className="text-gold text-lg leading-none my-1">{'\u2193'}</div>
          )}
        </div>
      ))}
    </div>
  )
}

function VisualFunnel({ config }: { config: Record<string, unknown> }) {
  const tiers = (config.tiers ?? []) as Array<{ label: string; percentage: string }>
  const total = config.total as string | undefined
  return (
    <div className="flex flex-col gap-2 mt-4">
      {tiers.map((tier, i) => (
        <div
          key={i}
          className="bg-surface border border-border rounded-lg p-3 flex items-center justify-between"
          style={{ marginLeft: i * 16, marginRight: i * 16 }}
        >
          <span className="text-text-primary text-sm">{tier.label}</span>
          <span className="text-gold font-mono text-sm">{tier.percentage}</span>
        </div>
      ))}
      {total && (
        <div className="text-center text-gold font-mono text-sm mt-2">{total}</div>
      )}
    </div>
  )
}

function VisualTrafficLight({ config }: { config: Record<string, unknown> }) {
  const lights = [
    { key: 'red', color: 'bg-risk-red', data: config.red as { label: string; example: string } | undefined },
    { key: 'yellow', color: 'bg-risk-yellow', data: config.yellow as { label: string; example: string } | undefined },
    { key: 'green', color: 'bg-risk-green', data: config.green as { label: string; example: string } | undefined },
  ]
  return (
    <div className="flex flex-col gap-3 mt-4">
      {lights.map((light) =>
        light.data ? (
          <div key={light.key} className="flex items-center gap-3">
            <div className={`w-4 h-4 rounded-full ${light.color} shrink-0`} />
            <div>
              <div className="text-text-primary text-sm font-semibold">{light.data.label}</div>
              <div className="text-text-muted text-xs">{light.data.example}</div>
            </div>
          </div>
        ) : null,
      )}
    </div>
  )
}

function ComparisonSplit({ config }: { config: Record<string, unknown> }) {
  const left = config.left as { label: string; items: string[] } | undefined
  const right = config.right as { label: string; items: string[] } | undefined
  if (!left || !right) return null
  return (
    <SplitScreen
      className="mt-4"
      leftLabel={left.label}
      rightLabel={right.label}
      left={
        <ul className="space-y-2">
          {left.items.map((item, i) => (
            <li key={i} className="text-text-muted text-sm">{item}</li>
          ))}
        </ul>
      }
      right={
        <ul className="space-y-2">
          {right.items.map((item, i) => (
            <li key={i} className="text-text-primary text-sm">{item}</li>
          ))}
        </ul>
      }
    />
  )
}

function DiagramVisual({ visual, fallbackContent }: { visual?: VisualConfig; fallbackContent: string }) {
  if (!visual) {
    return (
      <BodyReveal className="mt-4">
        <p className="text-text-muted text-sm italic">{fallbackContent}</p>
      </BodyReveal>
    )
  }

  switch (visual.type) {
    case 'pipeline':
      return <PipelineVisualizer className="mt-4" />
    case 'scorecard':
      return <ScoreCard className="mt-4" />
    case 'deployment':
      return <DeploymentMap className="mt-4" />
    case 'architecture':
      return <ArchitectureDiagram className="mt-4" />
    case 'flow':
      return <VisualFlow config={visual.config} />
    case 'funnel':
      return <VisualFunnel config={visual.config} />
    case 'grid':
    case 'stats-grid':
      return <VisualGrid config={visual.config} />
    case 'comparison':
      return <ComparisonSplit config={visual.config} />
    case 'traffic-light':
      return <VisualTrafficLight config={visual.config} />
    case 'constellation':
      return <ArchitectureDiagram className="mt-4" />
    case 'gauge':
    case 'fortress':
    case 'word-mockup':
    case 'pricing':
    case 'security-layers':
    default:
      // Fallback: render textual description
      return (
        <BodyReveal className="mt-4">
          <p className="text-text-muted text-sm italic">{fallbackContent}</p>
        </BodyReveal>
      )
  }
}

/* ------------------------------------------------------------------ */
/*  Section renderer                                                  */
/* ------------------------------------------------------------------ */

function SectionRenderer({ section }: { section: Section }) {
  switch (section.type) {
    case 'text':
      return (
        <BodyReveal>
          <p>{section.content}</p>
        </BodyReveal>
      )

    case 'quote':
      return (
        <BodyReveal>
          <blockquote className="border-l-4 border-gold pl-4 italic text-text-muted leading-relaxed">
            {section.content}
          </blockquote>
        </BodyReveal>
      )

    case 'code':
      return <CodeTyper code={section.content} language="" />

    case 'counter': {
      const cfg = section.visual?.config as
        | { target: number; prefix?: string; suffix?: string; subtext?: string }
        | undefined
      return (
        <div>
          <BodyReveal>
            <p className="mb-4">{section.content}</p>
          </BodyReveal>
          {cfg && (
            <div>
              <CounterReveal
                target={cfg.target}
                prefix={cfg.prefix ?? ''}
                suffix={cfg.suffix ?? ''}
              />
              {cfg.subtext && (
                <p className="text-text-muted text-sm mt-2 font-mono">{cfg.subtext}</p>
              )}
            </div>
          )}
        </div>
      )
    }

    case 'split-screen': {
      const visual = section.visual
      if (visual?.type === 'comparison') {
        return (
          <div>
            <BodyReveal>
              <p className="mb-4">{section.content}</p>
            </BodyReveal>
            <ComparisonSplit config={visual.config} />
          </div>
        )
      }
      if (visual?.type === 'traffic-light') {
        return (
          <div>
            <BodyReveal>
              <p className="mb-4">{section.content}</p>
            </BodyReveal>
            <VisualTrafficLight config={visual.config} />
          </div>
        )
      }
      if (visual?.type === 'pricing') {
        const tiers = ((visual.config.tiers ?? []) as Array<{ name: string; scans: number | string; price: string }>)
        return (
          <div>
            <BodyReveal>
              <p className="mb-4">{section.content}</p>
            </BodyReveal>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
              {tiers.map((tier, i) => (
                <div key={i} className="bg-surface border border-border rounded-lg p-3 text-center">
                  <div className="text-gold font-mono text-xs">{tier.name}</div>
                  <div className="text-text-primary text-lg font-serif mt-1">{tier.price}</div>
                  <div className="text-text-muted text-xs mt-1">{tier.scans} scans</div>
                </div>
              ))}
            </div>
          </div>
        )
      }
      // Fallback for other visual types inside split-screen
      return (
        <BodyReveal>
          <p>{section.content}</p>
        </BodyReveal>
      )
    }

    case 'diagram':
      return (
        <div>
          <BodyReveal>
            <p className="mb-2">{section.content}</p>
          </BodyReveal>
          <DiagramVisual visual={section.visual} fallbackContent={section.content} />
        </div>
      )

    default:
      return (
        <BodyReveal>
          <p>{section.content}</p>
        </BodyReveal>
      )
  }
}

/* ------------------------------------------------------------------ */
/*  ChapterRenderer                                                   */
/* ------------------------------------------------------------------ */

interface ChapterRendererProps {
  chapter: Chapter
  onChapterComplete?: () => void
}

export default function ChapterRenderer({ chapter, onChapterComplete }: ChapterRendererProps) {
  return (
    <div className="py-8">
      <ScrollSection onLeave={onChapterComplete}>
        <TextReveal as="h2">{chapter.title}</TextReveal>
      </ScrollSection>

      {chapter.sections.map((section, i) => (
        <div key={i}>
          {i > 0 && <ScanDivider className="my-8" />}
          <ScrollSection>
            <SectionRenderer section={section} />
          </ScrollSection>
        </div>
      ))}
    </div>
  )
}
