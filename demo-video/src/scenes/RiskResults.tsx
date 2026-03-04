import React from "react";
import {
    AbsoluteFill,
    useCurrentFrame,
    interpolate,
    spring,
    useVideoConfig,
} from "remotion";

const RISKS = [
    {
        level: "CRITICAL",
        color: "#ef4444",
        bgColor: "rgba(239, 68, 68, 0.15)",
        title: "Unlimited Indemnification",
        clause: "Clause 1.1",
        excerpt:
            '"...shall indemnify for all claims WITHOUT ANY LIMITATION OR CAP on liability."',
        explanation:
            "Unlimited liability for third-party claims creates extreme financial risk.",
        fix: "Limit indemnification to specific, capped damages as per Section 6.2(a).",
        delay: 30,
    },
    {
        level: "CRITICAL",
        color: "#ef4444",
        bgColor: "rgba(239, 68, 68, 0.15)",
        title: "Auto-Renewal Lock-In",
        clause: "Clause 2.1",
        excerpt:
            '"...automatically renew for successive 3-year terms unless terminated with 180 days notice."',
        explanation:
            "Long renewal period without performance review creates long-term obligation risk.",
        fix: "Change renewal period to 1 year and require affirmative renewal acceptance.",
        delay: 90,
    },
    {
        level: "WARNING",
        color: "#f59e0b",
        bgColor: "rgba(245, 158, 11, 0.15)",
        title: "Weak Security Guarantees",
        clause: "Clause 3.1",
        excerpt:
            '"...makes no guarantees regarding data breach prevention or notification timelines."',
        explanation:
            "Lack of breach notification obligations violates most regulatory requirements.",
        fix: 'Add: "Provider shall notify Client within 72 hours of any confirmed breach."',
        delay: 150,
    },
];

export const RiskResults: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Enter
    const enterOpacity = interpolate(frame, [0, 15], [0, 1], {
        extrapolateRight: "clamp",
    });

    // Counter animation
    const criticalCount = Math.round(
        interpolate(frame, [10, 40], [0, 2], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
        })
    );
    const warningCount = Math.round(
        interpolate(frame, [15, 45], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
        })
    );
    const safeCount = Math.round(
        interpolate(frame, [20, 50], [0, 3], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
        })
    );

    // Exit fade
    const exitOpacity = interpolate(frame, [370, 390], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    return (
        <AbsoluteFill
            style={{
                backgroundColor: "#0a0a0a",
                fontFamily: "'Inter', system-ui, sans-serif",
                opacity: enterOpacity * exitOpacity,
                display: "flex",
                flexDirection: "row",
            }}
        >
            {/* Left side: Risk Summary */}
            <div
                style={{
                    width: "40%",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    alignItems: "center",
                    padding: 60,
                }}
            >
                <h2
                    style={{
                        fontSize: 32,
                        fontWeight: 700,
                        color: "#ffffff",
                        margin: "0 0 12px",
                    }}
                >
                    Risk Summary
                </h2>
                <p
                    style={{
                        fontSize: 14,
                        color: "#64748b",
                        margin: "0 0 40px",
                    }}
                >
                    6 clauses analyzed in 3.2 seconds
                </p>

                {/* Counter cards */}
                <div
                    style={{
                        display: "flex",
                        gap: 16,
                        width: "100%",
                        maxWidth: 400,
                    }}
                >
                    {[
                        {
                            label: "Critical",
                            color: "#ef4444",
                            count: criticalCount,
                        },
                        {
                            label: "Warning",
                            color: "#f59e0b",
                            count: warningCount,
                        },
                        { label: "Safe", color: "#22c55e", count: safeCount },
                    ].map((item) => (
                        <div
                            key={item.label}
                            style={{
                                flex: 1,
                                textAlign: "center",
                                padding: "20px 0",
                                backgroundColor: "#141414",
                                borderRadius: 12,
                                border: "1px solid #2a2a2a",
                            }}
                        >
                            <div
                                style={{
                                    fontSize: 36,
                                    fontWeight: 700,
                                    color: item.color,
                                }}
                            >
                                {item.count}
                            </div>
                            <div
                                style={{
                                    fontSize: 12,
                                    color: "#666",
                                    marginTop: 4,
                                }}
                            >
                                {item.label}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right side: Risk Cards */}
            <div
                style={{
                    width: "60%",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    padding: "40px 60px 40px 20px",
                    gap: 16,
                    overflow: "hidden",
                }}
            >
                {RISKS.map((risk, i) => {
                    const cardFrame = frame - risk.delay;
                    const cardOpacity = interpolate(cardFrame, [0, 15], [0, 1], {
                        extrapolateLeft: "clamp",
                        extrapolateRight: "clamp",
                    });
                    const cardY = interpolate(cardFrame, [0, 15], [30, 0], {
                        extrapolateLeft: "clamp",
                        extrapolateRight: "clamp",
                    });

                    // Show fix after card appears
                    const fixOpacity = interpolate(cardFrame, [25, 40], [0, 1], {
                        extrapolateLeft: "clamp",
                        extrapolateRight: "clamp",
                    });

                    return (
                        <div
                            key={i}
                            style={{
                                opacity: cardOpacity,
                                transform: `translateY(${cardY}px)`,
                                backgroundColor: "#1f1f1f",
                                border: "1px solid #2a2a2a",
                                borderRadius: 12,
                                padding: 20,
                            }}
                        >
                            {/* Header */}
                            <div
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    marginBottom: 8,
                                }}
                            >
                                <div
                                    style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 10,
                                    }}
                                >
                                    <span
                                        style={{
                                            fontSize: 10,
                                            fontWeight: 700,
                                            padding: "4px 10px",
                                            borderRadius: 4,
                                            textTransform: "uppercase",
                                            letterSpacing: 0.5,
                                            backgroundColor: risk.bgColor,
                                            color: risk.color,
                                        }}
                                    >
                                        {risk.level}
                                    </span>
                                    <span
                                        style={{
                                            fontSize: 14,
                                            fontWeight: 600,
                                            color: "#ffffff",
                                        }}
                                    >
                                        {risk.title}
                                    </span>
                                </div>
                                <span
                                    style={{
                                        fontSize: 12,
                                        color: "#666",
                                    }}
                                >
                                    {risk.clause}
                                </span>
                            </div>

                            {/* Excerpt */}
                            <div
                                style={{
                                    fontSize: 12,
                                    color: "#94a3b8",
                                    fontFamily:
                                        "'Georgia', 'Times New Roman', serif",
                                    fontStyle: "italic",
                                    lineHeight: 1.6,
                                    padding: "8px 12px",
                                    backgroundColor: "#141414",
                                    borderRadius: 6,
                                    borderLeft: "2px solid #333",
                                    marginBottom: 10,
                                }}
                            >
                                {risk.excerpt}
                            </div>

                            {/* Fix */}
                            <div
                                style={{
                                    opacity: fixOpacity,
                                    fontSize: 12,
                                    color: "#e5e7eb",
                                    padding: "10px 12px",
                                    backgroundColor: "rgba(34, 197, 94, 0.08)",
                                    border: "1px solid rgba(34, 197, 94, 0.2)",
                                    borderLeft: "3px solid #22c55e",
                                    borderRadius: 6,
                                    lineHeight: 1.6,
                                }}
                            >
                                <strong
                                    style={{
                                        color: "#22c55e",
                                        fontSize: 10,
                                        textTransform: "uppercase",
                                        letterSpacing: 0.5,
                                        display: "block",
                                        marginBottom: 4,
                                    }}
                                >
                                    Suggested Fix
                                </strong>
                                {risk.fix}
                            </div>
                        </div>
                    );
                })}
            </div>
        </AbsoluteFill>
    );
};
