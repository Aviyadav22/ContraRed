import { useParams, Navigate } from 'react-router-dom'
import Layout from '../../../components/shell/Layout'
import ScanDivider from '../../../components/shell/ScanDivider'
import ScrollSection from '../../../components/scroll/ScrollSection'
import TextReveal from '../../../components/scroll/TextReveal'
import BodyReveal from '../../../components/scroll/BodyReveal'
import CodeTyper from '../../../components/scroll/CodeTyper'
import CounterReveal from '../../../components/scroll/CounterReveal'
import SplitScreen from '../../../components/scroll/SplitScreen'
import { useProgress } from '../../../stores/useProgress'

export default function ContraRedSession() {
  const { sessionId } = useParams()
  const id = Number(sessionId)
  const session = useProgress((s) => s.books.contrared?.sessions[id])
  if (session?.status === 'locked') {
    return <Navigate to="/locked" replace />
  }

  return (
    <Layout
      sessionLabel={`Session ${sessionId} of 4`}
      progress={{ current: 2, total: 5, label: 'Ch 2 of 5' }}
    >
      <div className="max-w-3xl mx-auto px-6 py-12">
        <ScrollSection>
          <TextReveal as="h1">The ContraRed Chronicle</TextReveal>
          <BodyReveal className="mt-6">
            <p>This is the story of how ContraRed was built — from a chance meeting to a working product that real lawyers use every day.</p>
          </BodyReveal>
        </ScrollSection>

        <ScanDivider className="my-8" />

        <ScrollSection>
          <TextReveal>The Cost of Manual Review</TextReveal>
          <div className="mt-8 flex gap-12">
            <CounterReveal target={72000} prefix="₹" suffix=" per review" />
            <CounterReveal target={40} suffix=" hours saved" />
          </div>
        </ScrollSection>

        <ScanDivider className="my-8" />

        <ScrollSection>
          <TextReveal>The First Prototype</TextReveal>
          <CodeTyper
            className="mt-6"
            language="python"
            code={`def scan_contract(text):\n    risks = []\n    for pattern in RISK_PATTERNS:\n        if re.search(pattern, text):\n            risks.append(pattern)\n    return risks`}
          />
        </ScrollSection>

        <ScanDivider className="my-8" />

        <ScrollSection>
          <TextReveal>The Big Decision</TextReveal>
          <SplitScreen
            className="mt-6"
            leftLabel="Rejected"
            rightLabel="Chosen"
            leftFade
            rightGlow
            left={<p className="text-text-muted">Standalone Desktop App — Too much friction</p>}
            right={<p className="text-text-primary">Word Add-in — Zero workflow disruption</p>}
          />
        </ScrollSection>
      </div>
    </Layout>
  )
}
