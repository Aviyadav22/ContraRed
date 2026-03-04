import React from "react";
import {
    AbsoluteFill,
    useCurrentFrame,
    interpolate,
    spring,
    useVideoConfig,
    Img,
    staticFile,
} from "remotion";

export const ClosingCTA: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Logo enter
    const logoScale = spring({
        fps,
        frame,
        config: { damping: 12, stiffness: 100 },
    });
    const logoOpacity = interpolate(frame, [0, 20], [0, 1], {
        extrapolateRight: "clamp",
    });

    // Tagline
    const taglineOpacity = interpolate(frame, [30, 50], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });
    const taglineY = interpolate(frame, [30, 50], [30, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    // URL
    const urlOpacity = interpolate(frame, [60, 80], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    // Button
    const buttonOpacity = interpolate(frame, [80, 100], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });
    const buttonScale = spring({
        fps,
        frame: Math.max(0, frame - 80),
        config: { damping: 10, stiffness: 120 },
    });

    return (
        <AbsoluteFill
            style={{
                backgroundColor: "#0f172a",
                justifyContent: "center",
                alignItems: "center",
                fontFamily: "'Inter', system-ui, sans-serif",
            }}
        >
            {/* Logo */}
            <div
                style={{
                    transform: `scale(${logoScale})`,
                    opacity: logoOpacity,
                    marginBottom: 40,
                }}
            >
                <Img
                    src={staticFile("logo.png")}
                    style={{ height: 56 }}
                />
            </div>

            {/* Tagline */}
            <div
                style={{
                    opacity: taglineOpacity,
                    transform: `translateY(${taglineY}px)`,
                    marginBottom: 16,
                }}
            >
                <h2
                    style={{
                        fontSize: 48,
                        fontWeight: 700,
                        color: "#ffffff",
                        margin: 0,
                        letterSpacing: -1,
                    }}
                >
                    Contract review, simplified.
                </h2>
            </div>

            {/* URL */}
            <div style={{ opacity: urlOpacity, marginBottom: 40 }}>
                <p
                    style={{
                        fontSize: 20,
                        color: "#94a3b8",
                        margin: 0,
                    }}
                >
                    contrared.ai
                </p>
            </div>

            {/* Download Button */}
            <div
                style={{
                    opacity: buttonOpacity,
                    transform: `scale(${buttonScale})`,
                }}
            >
                <div
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 10,
                        backgroundColor: "#ffffff",
                        color: "#0f172a",
                        padding: "16px 32px",
                        borderRadius: 10,
                        fontSize: 16,
                        fontWeight: 600,
                    }}
                >
                    <svg
                        width="20"
                        height="20"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                    </svg>
                    Download for Word
                </div>
            </div>
        </AbsoluteFill>
    );
};
