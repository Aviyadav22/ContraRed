import React from "react";
import {
    AbsoluteFill,
    useCurrentFrame,
    interpolate,
    spring,
    useVideoConfig,
} from "remotion";

const CONTRACT_LINES = [
    { type: "title", text: "MASTER SERVICES AGREEMENT" },
    { type: "subtitle", text: "ACME CORP & SYNERGY SOLUTIONS" },
    { type: "spacer" },
    {
        type: "body",
        text: 'This Master Services Agreement ("Agreement") is entered into as of January 15, 2026, by and between Acme Corporation ("Client") and Synergy Solutions Inc. ("Provider").',
    },
    { type: "spacer" },
    { type: "heading", text: "1. INDEMNIFICATION" },
    {
        type: "body",
        text: "1.1  Provider shall indemnify Client for all claims, damages, losses, and expenses arising from or related to Provider's services, WITHOUT ANY LIMITATION OR CAP on liability.",
    },
    { type: "spacer" },
    { type: "heading", text: "2. TERMINATION" },
    {
        type: "body",
        text: "2.1  This Agreement shall automatically renew for successive 3-year terms unless terminated by Client with 180 days prior written notice.",
    },
    { type: "spacer" },
    { type: "heading", text: "3. DATA SECURITY" },
    {
        type: "body",
        text: "3.1  Provider shall implement commercially reasonable security measures. Provider makes no guarantees regarding data breach prevention or notification timelines.",
    },
];

export const WordDocument: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Window appears
    const windowScale = spring({
        fps,
        frame,
        config: { damping: 15, stiffness: 80 },
    });
    const windowOpacity = interpolate(frame, [0, 15], [0, 1], {
        extrapolateRight: "clamp",
    });

    // Sidebar slides in from right
    const sidebarX = interpolate(frame, [60, 90], [400, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });
    const sidebarOpacity = interpolate(frame, [60, 80], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    // Fade out
    const exitOpacity = interpolate(frame, [160, 180], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    return (
        <AbsoluteFill
            style={{
                backgroundColor: "#f1f5f9",
                justifyContent: "center",
                alignItems: "center",
                fontFamily: "'Inter', system-ui, sans-serif",
                opacity: exitOpacity,
            }}
        >
            <div
                style={{
                    width: 1600,
                    height: 900,
                    transform: `scale(${windowScale})`,
                    opacity: windowOpacity,
                    display: "flex",
                    borderRadius: 12,
                    overflow: "hidden",
                    boxShadow: "0 25px 60px rgba(0,0,0,0.15)",
                    border: "1px solid #e2e8f0",
                }}
            >
                {/* Word Document Area */}
                <div
                    style={{
                        flex: 1,
                        backgroundColor: "#ffffff",
                        display: "flex",
                        flexDirection: "column",
                    }}
                >
                    {/* Title Bar */}
                    <div
                        style={{
                            height: 40,
                            backgroundColor: "#1e3a5f",
                            display: "flex",
                            alignItems: "center",
                            padding: "0 16px",
                            gap: 8,
                        }}
                    >
                        <div
                            style={{
                                width: 12,
                                height: 12,
                                borderRadius: "50%",
                                backgroundColor: "#ef4444",
                            }}
                        />
                        <div
                            style={{
                                width: 12,
                                height: 12,
                                borderRadius: "50%",
                                backgroundColor: "#f59e0b",
                            }}
                        />
                        <div
                            style={{
                                width: 12,
                                height: 12,
                                borderRadius: "50%",
                                backgroundColor: "#22c55e",
                            }}
                        />
                        <span
                            style={{
                                color: "#ffffff",
                                fontSize: 13,
                                marginLeft: 12,
                                fontWeight: 500,
                            }}
                        >
                            MSA_AcmeCorp_2026.docx — Microsoft Word
                        </span>
                    </div>

                    {/* Toolbar */}
                    <div
                        style={{
                            height: 36,
                            backgroundColor: "#f8fafc",
                            borderBottom: "1px solid #e2e8f0",
                            display: "flex",
                            alignItems: "center",
                            padding: "0 16px",
                            gap: 20,
                            fontSize: 13,
                            color: "#475569",
                        }}
                    >
                        <span>File</span>
                        <span>Edit</span>
                        <span>Insert</span>
                        <span>Tools</span>
                        <span style={{ fontWeight: 600, color: "#0f172a" }}>
                            ContraRed
                        </span>
                    </div>

                    {/* Document Content */}
                    <div
                        style={{
                            flex: 1,
                            padding: "48px 80px",
                            overflow: "hidden",
                            fontFamily: "'Georgia', 'Times New Roman', serif",
                            lineHeight: 1.8,
                        }}
                    >
                        {CONTRACT_LINES.map((line, i) => {
                            const lineDelay = i * 2;
                            const lineOpacity = interpolate(
                                frame,
                                [10 + lineDelay, 20 + lineDelay],
                                [0, 1],
                                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                            );

                            if (line.type === "spacer") {
                                return <div key={i} style={{ height: 16 }} />;
                            }
                            if (line.type === "title") {
                                return (
                                    <h1
                                        key={i}
                                        style={{
                                            fontSize: 20,
                                            fontWeight: 700,
                                            color: "#0f172a",
                                            opacity: lineOpacity,
                                            textAlign: "center",
                                            fontFamily: "'Inter', sans-serif",
                                            margin: "0 0 4px",
                                            letterSpacing: 1.5,
                                        }}
                                    >
                                        {line.text}
                                    </h1>
                                );
                            }
                            if (line.type === "subtitle") {
                                return (
                                    <h2
                                        key={i}
                                        style={{
                                            fontSize: 14,
                                            fontWeight: 500,
                                            color: "#64748b",
                                            opacity: lineOpacity,
                                            textAlign: "center",
                                            fontFamily: "'Inter', sans-serif",
                                            margin: "0 0 16px",
                                        }}
                                    >
                                        {line.text}
                                    </h2>
                                );
                            }
                            if (line.type === "heading") {
                                return (
                                    <h3
                                        key={i}
                                        style={{
                                            fontSize: 15,
                                            fontWeight: 700,
                                            color: "#0f172a",
                                            opacity: lineOpacity,
                                            fontFamily: "'Inter', sans-serif",
                                            margin: "0 0 8px",
                                        }}
                                    >
                                        {line.text}
                                    </h3>
                                );
                            }
                            return (
                                <p
                                    key={i}
                                    style={{
                                        fontSize: 14,
                                        color: "#334155",
                                        opacity: lineOpacity,
                                        margin: "0 0 8px",
                                    }}
                                >
                                    {line.text}
                                </p>
                            );
                        })}
                    </div>
                </div>

                {/* ContraRed Sidebar */}
                <div
                    style={{
                        width: 360,
                        backgroundColor: "#0a0a0a",
                        borderLeft: "1px solid #2a2a2a",
                        transform: `translateX(${sidebarX}px)`,
                        opacity: sidebarOpacity,
                        display: "flex",
                        flexDirection: "column",
                        padding: 20,
                    }}
                >
                    {/* Sidebar Header */}
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            paddingBottom: 16,
                            borderBottom: "1px solid #2a2a2a",
                            marginBottom: 20,
                        }}
                    >
                        <span
                            style={{
                                fontSize: 16,
                                fontWeight: 700,
                                color: "#ffffff",
                                fontFamily: "'Inter', sans-serif",
                            }}
                        >
                            ContraRed
                        </span>
                    </div>

                    {/* Playbook Selector */}
                    <div style={{ marginBottom: 16 }}>
                        <span
                            style={{
                                fontSize: 11,
                                fontWeight: 600,
                                color: "#666",
                                textTransform: "uppercase",
                                letterSpacing: 0.8,
                                fontFamily: "'Inter', sans-serif",
                            }}
                        >
                            Playbook
                        </span>
                        <div
                            style={{
                                marginTop: 8,
                                padding: "10px 14px",
                                backgroundColor: "#141414",
                                border: "1px solid #2a2a2a",
                                borderRadius: 8,
                                color: "#ffffff",
                                fontSize: 13,
                                fontFamily: "'Inter', sans-serif",
                            }}
                        >
                            Default Rules
                        </div>
                    </div>

                    {/* Scan Button */}
                    <button
                        style={{
                            width: "100%",
                            padding: "12px 16px",
                            backgroundColor: "#ffffff",
                            color: "#000000",
                            border: "none",
                            borderRadius: 8,
                            fontSize: 13,
                            fontWeight: 600,
                            fontFamily: "'Inter', sans-serif",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 8,
                        }}
                    >
                        Scan Document
                    </button>

                    {/* Risk Summary placeholder */}
                    <div style={{ marginTop: 20 }}>
                        <span
                            style={{
                                fontSize: 11,
                                fontWeight: 600,
                                color: "#666",
                                textTransform: "uppercase",
                                letterSpacing: 0.8,
                                fontFamily: "'Inter', sans-serif",
                            }}
                        >
                            Risk Summary
                        </span>
                        <div
                            style={{
                                marginTop: 12,
                                display: "flex",
                                gap: 8,
                            }}
                        >
                            {[
                                { label: "Critical", color: "#ef4444", count: "—" },
                                { label: "Warning", color: "#f59e0b", count: "—" },
                                { label: "Safe", color: "#22c55e", count: "—" },
                            ].map((item) => (
                                <div
                                    key={item.label}
                                    style={{
                                        flex: 1,
                                        textAlign: "center",
                                        padding: "10px 0",
                                        backgroundColor: "#141414",
                                        borderRadius: 8,
                                        border: "1px solid #2a2a2a",
                                    }}
                                >
                                    <div
                                        style={{
                                            fontSize: 20,
                                            fontWeight: 700,
                                            color: item.color,
                                            fontFamily: "'Inter', sans-serif",
                                        }}
                                    >
                                        {item.count}
                                    </div>
                                    <div
                                        style={{
                                            fontSize: 10,
                                            color: "#666",
                                            fontFamily: "'Inter', sans-serif",
                                            marginTop: 2,
                                        }}
                                    >
                                        {item.label}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </AbsoluteFill>
    );
};
