import { useState, type CSSProperties } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout';
import { Button, Badge } from '@/components/ui';
import { Modal } from '@/components/ui/Modal';
import { TextareaInput, TextInput, SelectInput } from '@/components/ui/Input';
import { FileText, Trash2, Edit3, UserPlus, AlertCircle } from 'lucide-react';
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function apiRequest<T = any>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    return fetch(url, { ...options, headers, credentials: 'include' }).then(r => {
        if (!r.ok) throw new Error('Request failed');
        return r.json();
    });
}

// API functions for rights
async function listRightsRequests() {
    return apiRequest<any[]>('/rights/requests');
}
async function requestDataAccess(notes?: string) {
    return apiRequest('/rights/access', { method: 'POST', body: JSON.stringify({ notes }) });
}
async function requestDataCorrection(data: { field_name: string; current_value?: string; corrected_value: string; reason?: string }) {
    return apiRequest('/rights/correction', { method: 'POST', body: JSON.stringify(data) });
}
async function requestDataErasure(reason?: string) {
    return apiRequest('/rights/erasure', { method: 'POST', body: JSON.stringify({ reason, confirm: true }) });
}
async function listNominations() {
    return apiRequest<any[]>('/rights/nominations');
}
async function createNomination(data: { nominee_name: string; nominee_email?: string; nominee_phone?: string; relationship?: string }) {
    return apiRequest('/rights/nomination', { method: 'POST', body: JSON.stringify(data) });
}
async function revokeNomination(id: string) {
    return apiRequest(`/rights/nominations/${id}`, { method: 'DELETE' });
}
async function listGrievances() {
    return apiRequest<any[]>('/grievances/');
}
async function submitGrievance(data: { category: string; description: string }) {
    return apiRequest('/grievances/', { method: 'POST', body: JSON.stringify(data) });
}

const sectionStyle: CSSProperties = {
    marginBottom: 32,
    padding: 24,
    borderRadius: 12,
    border: '1px solid var(--border)',
    backgroundColor: 'var(--bg-secondary)',
};

const statusColors: Record<string, string> = {
    submitted: 'var(--text-muted)',
    acknowledged: 'var(--accent)',
    in_progress: 'var(--accent)',
    completed: 'var(--green)',
    resolved: 'var(--green)',
    rejected: 'var(--red)',
    escalated: 'var(--red)',
};

export default function DataRights() {
    const queryClient = useQueryClient();
    const [showAccessModal, setShowAccessModal] = useState(false);
    const [showCorrectionModal, setShowCorrectionModal] = useState(false);
    const [showErasureModal, setShowErasureModal] = useState(false);
    const [showNominationModal, setShowNominationModal] = useState(false);
    const [showGrievanceModal, setShowGrievanceModal] = useState(false);

    // Form state
    const [accessNotes, setAccessNotes] = useState('');
    const [correctionField, setCorrectionField] = useState('');
    const [correctionCurrent, setCorrectionCurrent] = useState('');
    const [correctionNew, setCorrectionNew] = useState('');
    const [correctionReason, setCorrectionReason] = useState('');
    const [erasureReason, setErasureReason] = useState('');
    const [nomineeName, setNomineeName] = useState('');
    const [nomineeEmail, setNomineeEmail] = useState('');
    const [nomineeRelationship, setNomineeRelationship] = useState('');
    const [grievanceCategory, setGrievanceCategory] = useState('consent_violation');
    const [grievanceDescription, setGrievanceDescription] = useState('');

    const { data: requests } = useQuery({ queryKey: ['rights-requests'], queryFn: listRightsRequests });
    const { data: nominations } = useQuery({ queryKey: ['nominations'], queryFn: listNominations });
    const { data: grievances } = useQuery({ queryKey: ['grievances'], queryFn: listGrievances });

    const accessMut = useMutation({
        mutationFn: () => requestDataAccess(accessNotes || undefined),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['rights-requests'] }); setShowAccessModal(false); },
    });
    const correctionMut = useMutation({
        mutationFn: () => requestDataCorrection({ field_name: correctionField, current_value: correctionCurrent || undefined, corrected_value: correctionNew, reason: correctionReason || undefined }),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['rights-requests'] }); setShowCorrectionModal(false); },
    });
    const erasureMut = useMutation({
        mutationFn: () => requestDataErasure(erasureReason || undefined),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['rights-requests'] }); setShowErasureModal(false); },
    });
    const nominationMut = useMutation({
        mutationFn: () => createNomination({ nominee_name: nomineeName, nominee_email: nomineeEmail || undefined, relationship: nomineeRelationship || undefined }),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['nominations'] }); setShowNominationModal(false); },
    });
    const grievanceMut = useMutation({
        mutationFn: () => submitGrievance({ category: grievanceCategory, description: grievanceDescription }),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['grievances'] }); setShowGrievanceModal(false); },
    });

    return (
        <AppLayout>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: 8 }}>
                Your Data Rights
            </h1>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 32 }}>
                Under India's DPDP Act, you have the right to access, correct, and delete your personal data, nominate a representative, and file grievances.
            </p>

            {/* Action Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16, marginBottom: 32 }}>
                <ActionCard icon={<FileText size={20} />} title="Export My Data" description="Download all personal data we hold about you" onClick={() => setShowAccessModal(true)} />
                <ActionCard icon={<Edit3 size={20} />} title="Correct My Data" description="Request correction of inaccurate information" onClick={() => setShowCorrectionModal(true)} />
                <ActionCard icon={<Trash2 size={20} />} title="Delete My Account" description="Request permanent erasure of your data" onClick={() => setShowErasureModal(true)} color="var(--red)" />
                <ActionCard icon={<UserPlus size={20} />} title="Nominate Representative" description="Designate someone to act on your behalf" onClick={() => setShowNominationModal(true)} />
                <ActionCard icon={<AlertCircle size={20} />} title="File Grievance" description="Report a privacy concern or violation" onClick={() => setShowGrievanceModal(true)} />
            </div>

            {/* Active Requests */}
            {requests && requests.length > 0 && (
                <div style={sectionStyle}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Your Requests</h2>
                    {requests.map((r: any) => (
                        <div key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: statusColors[r.status] || 'var(--text-muted)' }} />
                            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', flex: 1 }}>
                                {r.request_type.toUpperCase()} request
                            </span>
                            <Badge variant="neutral">{r.status}</Badge>
                            {r.resolution_deadline && (
                                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                    Due: {new Date(r.resolution_deadline).toLocaleDateString('en-IN')}
                                </span>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Nominations */}
            {nominations && nominations.length > 0 && (
                <div style={sectionStyle}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Nominations</h2>
                    {nominations.map((n: any) => (
                        <div key={n.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                            <UserPlus size={16} style={{ color: 'var(--accent)' }} />
                            <span style={{ flex: 1, fontSize: 13, color: 'var(--text-primary)' }}>{n.nominee_name} {n.relationship && `(${n.relationship})`}</span>
                            <Button variant="ghost" size="sm" onClick={() => { revokeNomination(n.id).then(() => queryClient.invalidateQueries({ queryKey: ['nominations'] })); }}>
                                Revoke
                            </Button>
                        </div>
                    ))}
                </div>
            )}

            {/* Grievances */}
            {grievances && grievances.length > 0 && (
                <div style={sectionStyle}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Grievances</h2>
                    {grievances.map((g: any) => (
                        <div key={g.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                            <AlertCircle size={16} style={{ color: statusColors[g.status] || 'var(--text-muted)' }} />
                            <span style={{ flex: 1, fontSize: 13, color: 'var(--text-primary)' }}>{g.category.replace('_', ' ')}</span>
                            <Badge variant="neutral">{g.status}</Badge>
                            {g.resolution_deadline && (
                                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                    Due: {new Date(g.resolution_deadline).toLocaleDateString('en-IN')}
                                </span>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Modals */}
            {showAccessModal && (
                <Modal open={true} title="Export Your Data" onClose={() => setShowAccessModal(false)}>
                    <div style={{ padding: 24 }}>
                        <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 16 }}>
                            We will prepare a complete export of all personal data we hold about you. This is your right under DPDP Act Section 11.
                        </p>
                        <TextareaInput label="Additional Notes (optional)" value={accessNotes} onChange={e => setAccessNotes(e.target.value)} placeholder="Any specific data you're looking for..." />
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 16 }}>
                            <Button variant="ghost" onClick={() => setShowAccessModal(false)}>Cancel</Button>
                            <Button variant="primary" onClick={() => accessMut.mutate()} disabled={accessMut.isPending}>
                                {accessMut.isPending ? 'Submitting...' : 'Request Export'}
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}

            {showCorrectionModal && (
                <Modal open={true} title="Request Data Correction" onClose={() => setShowCorrectionModal(false)}>
                    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <TextInput label="Field to Correct" value={correctionField} onChange={e => setCorrectionField(e.target.value)} placeholder="e.g., name, email" />
                        <TextInput label="Current Value" value={correctionCurrent} onChange={e => setCorrectionCurrent(e.target.value)} placeholder="What it currently shows" />
                        <TextInput label="Correct Value" value={correctionNew} onChange={e => setCorrectionNew(e.target.value)} placeholder="What it should be" />
                        <TextareaInput label="Reason" value={correctionReason} onChange={e => setCorrectionReason(e.target.value)} placeholder="Why this needs correction" />
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                            <Button variant="ghost" onClick={() => setShowCorrectionModal(false)}>Cancel</Button>
                            <Button variant="primary" onClick={() => correctionMut.mutate()} disabled={correctionMut.isPending || !correctionField || !correctionNew}>
                                Submit
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}

            {showErasureModal && (
                <Modal open={true} title="Delete Your Account" onClose={() => setShowErasureModal(false)}>
                    <div style={{ padding: 24 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, padding: 16, borderRadius: 8, backgroundColor: 'rgba(239,68,68,0.1)' }}>
                            <AlertCircle size={24} style={{ color: 'var(--red)', flexShrink: 0 }} />
                            <p style={{ fontSize: 14, color: 'var(--text-primary)', margin: 0 }}>
                                This action is irreversible. Your account will be permanently deactivated and all personal data anonymised.
                                Anonymised audit and consent logs will be retained for 7 years as required by law.
                            </p>
                        </div>
                        <TextareaInput label="Reason (optional)" value={erasureReason} onChange={e => setErasureReason(e.target.value)} placeholder="Help us improve by sharing why you're leaving" />
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 16 }}>
                            <Button variant="ghost" onClick={() => setShowErasureModal(false)}>Cancel</Button>
                            <Button variant="danger" onClick={() => erasureMut.mutate()} disabled={erasureMut.isPending}>
                                {erasureMut.isPending ? 'Submitting...' : 'Delete My Account'}
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}

            {showNominationModal && (
                <Modal open={true} title="Nominate Representative" onClose={() => setShowNominationModal(false)}>
                    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
                            Under DPDP Act Section 14, you can designate someone to exercise your data rights in case of death or incapacity.
                        </p>
                        <TextInput label="Nominee Name" value={nomineeName} onChange={e => setNomineeName(e.target.value)} placeholder="Full name" />
                        <TextInput label="Nominee Email" value={nomineeEmail} onChange={e => setNomineeEmail(e.target.value)} placeholder="email@example.com" />
                        <TextInput label="Relationship" value={nomineeRelationship} onChange={e => setNomineeRelationship(e.target.value)} placeholder="e.g., spouse, parent" />
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                            <Button variant="ghost" onClick={() => setShowNominationModal(false)}>Cancel</Button>
                            <Button variant="primary" onClick={() => nominationMut.mutate()} disabled={nominationMut.isPending || !nomineeName}>
                                Register Nominee
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}

            {showGrievanceModal && (
                <Modal open={true} title="File Grievance" onClose={() => setShowGrievanceModal(false)}>
                    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <SelectInput label="Category" value={grievanceCategory} onChange={e => setGrievanceCategory(e.target.value)}>
                            <option value="consent_violation">Consent Violation</option>
                            <option value="data_breach">Data Breach</option>
                            <option value="processing_error">Processing Error</option>
                            <option value="rights_denial">Rights Denial</option>
                            <option value="unauthorized_processing">Unauthorized Processing</option>
                            <option value="other">Other</option>
                        </SelectInput>
                        <TextareaInput label="Description" value={grievanceDescription} onChange={e => setGrievanceDescription(e.target.value)} placeholder="Describe your concern in detail (minimum 10 characters)" />
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                            <Button variant="ghost" onClick={() => setShowGrievanceModal(false)}>Cancel</Button>
                            <Button variant="primary" onClick={() => grievanceMut.mutate()} disabled={grievanceMut.isPending || grievanceDescription.length < 10}>
                                Submit Grievance
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}
        </AppLayout>
    );
}

function ActionCard({ icon, title, description, onClick, color }: {
    icon: React.ReactNode; title: string; description: string; onClick: () => void; color?: string;
}) {
    return (
        <button onClick={onClick} style={{
            padding: 20, borderRadius: 12, border: '1px solid var(--border)',
            backgroundColor: 'var(--bg-secondary)', cursor: 'pointer',
            textAlign: 'left', transition: 'border-color 0.2s',
            display: 'flex', flexDirection: 'column', gap: 8,
        }}>
            <div style={{ color: color || 'var(--accent)' }}>{icon}</div>
            <span style={{ fontSize: 14, fontWeight: 600, color: color || 'var(--text-primary)' }}>{title}</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{description}</span>
        </button>
    );
}
