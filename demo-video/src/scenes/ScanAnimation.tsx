import React from "react";
import {
    AbsoluteFill,
    useCurrentFrame,
    interpolate,
    spring,
    useVideoConfig,
} from "remotion";

const REASONING_STEPS = [
    { text: "Parsing document clauses...", delay: 0 },
    { text: "Checking indemnification scope...", delay: 15 },
    { text: "Analyzing termination provisions...", delay: 30 },
    { text: "Reviewing data security obligations...", delay: 45 },
    { text: "Detecting missing protections...", delay: 60 },
    { text: "Generating risk assessment...", delay: 75 },
];

export const ScanAnimation: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Overall appear
    const enterOpacity = interpolate(frame, [0, 15], [0, 1], {
        extrapolateRight: "clamp",
    });

    // Progress bar
    const progress = interpolate(frame, [10, 120], [0, 100], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    // Exit fade
    const exitOpacity = interpolate(frame, [130, 150], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    return (
        <AbsoluteFill
            style={{
                backgroundColor: "#0a0a0a",
                justifyContent: "center",
                alignItems: "center",
                fontFamily: "'Inter', system-ui, sans-serif",
                opacity: enterOpacity * exitOpacity,
            }}
        >
            <div style={{ width: 560, textAlign: "center" }}>
                {/* Title */}
                <h2
                    style={{
                        fontSize: 28,
                        fontWeight: 700,
                        color: "#ffffff",
                        margin: "0 0 8px",
                    }}
                >
                    Analyzing Contract...
                </h2>
                <p
                    style={{
                        fontSize: 14,
                        color: "#64748b",
                        margin: "0 0 40px",
                    }}
                >
                    MSA_AcmeCorp_2026.docx
                </p>

                {/* Progress Bar */}
                <div
                    style={{
                        height: 6,
                        backgroundColor: "#1e293b",
                        borderRadius: 3,
                        overflow: "hidden",
                        marginBottom: 40,
                    }}
                >
                    <div
                        style={{
                            width: `${progress}%`,
                            height: "100%",
                            backgroundColor: "#ffffff",
                            borderRadius: 3,
                            transition: "width 0.1s",
                        }}
                    />
                </div>

                {/* Reasoning Steps */}
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 12,
                        alignItems: "flex-start",
                    }}
                >
                    {REASONING_STEPS.map((step, i) => {
                        const stepFrame = frame - step.delay;
                        const isActive = stepFrame >= 0;
                        const isComplete = stepFrame > 20;

                        const stepOpacity = interpolate(
                            stepFrame,
                            [0, 8],
                            [0, 1],
                            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                        );

                        const stepX = interpolate(
                            stepFrame,
                            [0, 8],
                            [-15, 0],
                            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                        );

                        if (!isActive) return null;

                        return (
                            <div
                                key={i}
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 12,
                                    opacity: stepOpacity * (isComplete ? 0.4 : 1),
                                    transform: `translateX(${stepX}px)`,
                                }}
                            >
                                {/* Indicator */}
                                <div
                                    style={{
                                        width: 18,
                                        height: 18,
                                        borderRadius: "50%",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        fontSize: 10,
                                        ...(isComplete
                                            ? { backgroundColor: "#22c55e", color: "#fff" }
                                            : {
                                                border: "2px solid #818cf8",
                                                boxShadow: "0 0 8px rgba(129,140,248,0.4)",
                                            }),
                                    }}
                                >
                                    {isComplete ? "✓" : ""}
                                </div>

                                {/* Text */}
                                <span
                                    style={{
                                        fontSize: 14,
                                        color: "#e5e7eb",
                                        fontFamily:
                                            "'SF Mono', 'Monaco', 'Consolas', monospace",
                                    }}
                                >
                                    {step.text}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>
        </AbsoluteFill>
    );
};
