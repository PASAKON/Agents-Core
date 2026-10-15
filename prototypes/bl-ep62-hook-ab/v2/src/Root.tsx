import React from 'react';
import { Composition } from 'remotion';
import { Hook } from './Hook';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Hook"
      component={Hook}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={450}
    />
  );
};
