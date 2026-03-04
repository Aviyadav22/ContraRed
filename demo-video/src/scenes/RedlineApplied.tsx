import React from "react";
import {
    AbsoluteFill,
    useCurrentFrame,
    interpolate,
    spring,
    useVideoConfig,
} from "remotion";

export const RedlineApplied: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Zoom into document
    const enterScale = spring({
        fps,
        frame,
        config: { damping: 15, stiffness: 60 },
    });
    const enterOpacity = interpolate(frame, [0, 20], [0, 1], {
        extrapolateRight: "clamp",
    });

    // Strikethrough animation
    const strikeWidth = interpolate(frame, [40, 80], [0, 100], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    // Replacement text
    const replaceOpacity = interpolate(frame, [90, 110], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });
    const replaceY = interpolate(frame, [90, 110], [10, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    // Second clause strikethrough
    const strike2Width = interpolate(frame, [140, 180], [0, 100], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });
    const replace2Opacity = interpolate(frame, [190, 210], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });
    const replace2Y = interpolate(frame, [190, 210], [10, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    // "Changes applied" badge
    const badgeOpacity = interpolate(frame, [230, 250], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });
    const badgeScale = spring({
        fps,
        frame: Math.max(0, frame - 230),
        config: { damping: 10, stiffness: 120 },
    });

    // Exit
    const exitOpacity = interpolate(frame, [270, 300], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    return (
        <AbsoluteFill
            style={{
                backgroundColor: "#ffffff",
                justifyContent: "center",
                alignItems: "center",
                fontFamily: "'Inter', system-ui, sans-serif",
                opacity: enterOpacity * exitOpacity,
            }}
        >
            {/* Zoomed-in document view */}
            <div
                style={{
                    width: 1200,
                    transform: `scale(${enterScale})`,
                    padding: "60px 100px",
                    backgroundColor: "#ffffff",
                    borderRadius: 12,
                    boxShadow: "0 20px 60px rgba(0,0,0,0.08)",
                    border: "1px solid #e2e8f0",
                }}
            >
                {/* Section header */}
                <h3
                    style={{
                        fontSize: 16,
                        fontWeight: 700,
                        color: "#0f172a",
                        margin: "0 0 24px",
                        paddingBottom: 12,
                        borderBottom: "1px solid #e2e8f0",
                    }}
                >
                    1. INDEMNIFICATION
                </h3>

                {/* Original clause with strikethrough */}
                <div style={{ marginBottom: 32 }}>
                    <p
                        style={{
                            fontSize: 16,
                            lineHeight: 1.8,
                            color: "#334155",
                            fontFamily: "'Georgia', 'Times New Roman', serif",
                            margin: 0,
                        }}
                    >
                        1.1 Provider shall indemnify Client for all claims, damages,
                        losses, and expenses{" "}
                        <span
                            style={{
                                position: "relative",
                                display: "inline",
                            }}
                        >
                            <span
                                style={{
                                    color: "#ef4444",
                                    textDecoration: "line-through",
                                    textDecorationColor: "#ef4444",
                                    opacity: strikeWidth > 0 ? 1 : 0,
                                }}
                            >
                                WITHOUT ANY LIMITATION OR CAP on liability
                            </span>
                        </span>
                        .
                    </p>

                    {/* Replacement text */}
                    <div
                        style={{
                            opacity: replaceOpacity,
                            transform: `translateY(${replaceY}px)`,
                            marginTop: 8,
                            marginLeft: 0,
                        }}
                    >
                        <p
                            style={{
                                fontSize: 16,
                                lineHeight: 1.8,
                                color: "#2563EB",
                                fontFamily:
                                    "'Georgia', 'Times New Roman', serif",
                                margin: 0,
                                padding: "4px 8px",
                                backgroundColor: "rgba(37, 99, 235, 0.06)",
                                borderLeft: "3px solid #2563EB",
                                borderRadius: "0 4px 4px 0",
                            }}
                        >
                            subject to a maximum aggregate liability cap equal to the
                            total fees paid under this Agreement in the preceding 12
                            months, as specified in Section 6.2(a)
                        </p>
                    </div>
                </div>

                {/* Section header 2 */}
                <h3
                    style={{
                        fontSize: 16,
                        fontWeight: 700,
                        color: "#0f172a",
                        margin: "0 0 24px",
                        paddingBottom: 12,
                        borderBottom: "1px solid #e2e8f0",
                    }}
                >
                    2. TERMINATION
                </h3>

                {/* Second clause */}
                <div>
                    <p
                        style={{
                            fontSize: 16,
                            lineHeight: 1.8,
                            color: "#334155",
                            fontFamily: "'Georgia', 'Times New Roman', serif",
                            margin: 0,
                        }}
                    >
                        2.1 This Agreement shall automatically renew for successive{" "}
                        <span
                            style={{
                                color: "#ef4444",
                                textDecoration: "line-through",
                                textDecorationColor: "#ef4444",
                                opacity: strike2Width > 0 ? 1 : 0,
                            }}
                        >
                            3-year terms unless terminated by Client with 180 days
                        </span>{" "}
                        prior written notice.
                    </p>

                    <div
                        style={{
                            opacity: replace2Opacity,
                            transform: `translateY(${replace2Y}px)`,
                            marginTop: 8,
                        }}
                    >
                        <p
                            style={{
                                fontSize: 16,
                                lineHeight: 1.8,
                                color: "#2563EB",
                                fontFamily:
                                    "'Georgia', 'Times New Roman', serif",
                                margin: 0,
                                padding: "4px 8px",
                                backgroundColor: "rgba(37, 99, 235, 0.06)",
                                borderLeft: "3px solid #2563EB",
                                borderRadius: "0 4px 4px 0",
                            }}
                        >
                            1-year terms, subject to Client's affirmative renewal
                            acceptance, with 60 days
                        </p>
                    </div>
                </div>
            </div>

            {/* "Changes Applied" badge */}
            <div
                style={{
                    position: "absolute",
                    top: 80,
                    right: 120,
                    opacity: badgeOpacity,
                    transform: `scale(${badgeScale})`,
                    backgroundColor: "#22c55e",
                    color: "#ffffff",
                    padding: "12px 24px",
                    borderRadius: 8,
                    fontSize: 14,
                    fontWeight: 700,
                    boxShadow: "0 8px 20px rgba(34, 197, 94, 0.3)",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                }}
            >
                <span style={{ fontSize: 18 }}>✓</span>
                2 Redlines Applied
            </div>
        </AbsoluteFill>
    );
};
