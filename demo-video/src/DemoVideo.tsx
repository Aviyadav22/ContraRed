import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { TitleCard } from "./scenes/TitleCard";
import { WordDocument } from "./scenes/WordDocument";
import { ScanAnimation } from "./scenes/ScanAnimation";
import { RiskResults } from "./scenes/RiskResults";
import { RedlineApplied } from "./scenes/RedlineApplied";
import { ClosingCTA } from "./scenes/ClosingCTA";

// Scene timing (in frames at 30fps)
const SCENES = {
    title: { from: 0, duration: 90 },  // 0-3s
    word: { from: 90, duration: 180 },  // 3-9s
    scan: { from: 270, duration: 150 },  // 9-14s
    risks: { from: 420, duration: 390 },  // 14-27s
    redline: { from: 810, duration: 300 },  // 27-37s
    closing: { from: 1110, duration: 240 },  // 37-45s
};

export const DemoVideo: React.FC = () => {
    return (
        <AbsoluteFill style={{ backgroundColor: "#ffffff" }}>
            <Sequence from={SCENES.title.from} durationInFrames={SCENES.title.duration}>
                <TitleCard />
            </Sequence>

            <Sequence from={SCENES.word.from} durationInFrames={SCENES.word.duration}>
                <WordDocument />
            </Sequence>

            <Sequence from={SCENES.scan.from} durationInFrames={SCENES.scan.duration}>
                <ScanAnimation />
            </Sequence>

            <Sequence from={SCENES.risks.from} durationInFrames={SCENES.risks.duration}>
                <RiskResults />
            </Sequence>

            <Sequence from={SCENES.redline.from} durationInFrames={SCENES.redline.duration}>
                <RedlineApplied />
            </Sequence>

            <Sequence from={SCENES.closing.from} durationInFrames={SCENES.closing.duration}>
                <ClosingCTA />
            </Sequence>
        </AbsoluteFill>
    );
};
