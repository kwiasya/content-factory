import { Composition } from "remotion";
import styleJson from "../../style.json";
import { calculateOverlayMetadata, Overlay } from "./Overlay";
import { OverlayProps, Style } from "./style";

const style = styleJson as unknown as Style;

// Defaults are for Studio preview only; render.mjs always passes real props.
const defaultProps: OverlayProps = {
  text: "Potsdam, Sanssouci",
  type: "place",
  durationInFrames: 3 * style.canvas.fps,
  style,
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Overlay"
    component={Overlay}
    width={style.canvas.width}
    height={style.canvas.height}
    fps={style.canvas.fps}
    durationInFrames={defaultProps.durationInFrames}
    defaultProps={defaultProps}
    calculateMetadata={calculateOverlayMetadata}
  />
);
