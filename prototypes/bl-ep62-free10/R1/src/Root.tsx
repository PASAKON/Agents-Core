import React from 'react';
import { Composition } from 'remotion';
import { Clip } from './Clip';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Clip"
      component={Clip}
      durationInFrames={300}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};
