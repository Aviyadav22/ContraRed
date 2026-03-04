import React from "react";
import { Composition } from "remotion";
import { DemoVideo } from "./DemoVideo";

export const RemotionRoot: React.FC = () => {
    return (
        <Composition
            id="DemoVideo"
            component={DemoVideo}
            durationInFrames={1350}
            fps={30}
            width={1920}
            height={1080}
        />
    );
};
