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

export const TitleCard: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Logo fade + scale
    const logoOpacity = interpolate(frame, [0, 20], [0, 1], {
        extrapolateRight: "clamp",
    });
    const logoScale = spring({
        fps,
        frame,
        config: { damping: 12, stiffness: 100 },
    });

    // Headline slide up
    const headlineOpacity = interpolate(frame, [25, 45], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });
    const headlineY = interpolate(frame, [25, 45], [40, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    // Subline slide up (delayed)
    const sublineOpacity = interpolate(frame, [40, 60], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });
    const sublineY = interpolate(frame, [40, 60], [30, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    // Fade out at end
    const exitOpacity = interpolate(frame, [70, 90], [1, 0], {
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
                opacity: exitOpacity,
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
                    style={{ height: 64 }}
                />
            </div>

            {/* Headline */}
            <div
                style={{
                    opacity: headlineOpacity,
                    transform: `translateY(${headlineY}px)`,
                }}
            >
                <h1
                    style={{
                        fontSize: 72,
                        fontWeight: 700,
                        color: "#0f172a",
                        margin: 0,
                        letterSpacing: -2,
                        lineHeight: 1.1,
                        textAlign: "center",
                    }}
                >
                    Catch liabilities{" "}
                    <span style={{ color: "#dc2626" }}>before</span> you sign.
                </h1>
            </div>

            {/* Subline */}
            <div
                style={{
                    opacity: sublineOpacity,
                    transform: `translateY(${sublineY}px)`,
                    marginTop: 20,
                }}
            >
                <p
                    style={{
                        fontSize: 24,
                        color: "#64748b",
                        margin: 0,
                        fontWeight: 400,
                    }}
                >
                    Contract redlining for Microsoft Word
                </p>
            </div>
        </AbsoluteFill>
    );
};
