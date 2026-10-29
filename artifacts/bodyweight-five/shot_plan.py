"""Complementary views expose distinct muscle groups, not mirrored duplicates."""
import json
from pathlib import Path

def shot(label, position, target, scale):
    return dict(label=label, position=position, target=target, scale=scale)

SHOTS = {
    '5965': [shot('Movement / quads and core', [0,-6,1.15], [-.17,0,.90], 2.20),
             shot('Calves and glutes', [-3,5.5,1.2], [-.17,0,.90], 2.20)],
    '5915': [shot('Palms, chest and core', [5,-3,1.7], [0,-.10,.36], 2.20),
             shot('Triceps and glutes', [5,3.3,1.4], [0,-.10,.36], 2.20)],
    '5887': [shot('Shoulders, triceps and core', [5,-3,1.9], [0,.20,.65], 2.30),
             shot('Glutes and posterior stretch', [5,3.3,1.9], [0,.20,.65], 2.30)],
    '0001': [shot('Movement from the side', [6,-.05,.45], [0,-.05,.45], 1.95),
             shot('Abdominal detail', [0,-3.5,4.5], [0,-.05,.35], 1.95)],
    '9066': [shot('Travel and knee cushioning', [0,-6,1.3], [0,0,.88], 2.20),
             shot('Loaded calf and glute', [5.5,2.5,1.4], [0,0,.88], 2.20)],
}

if __name__ == '__main__':
    Path(__file__).with_name('camera-presets.json').write_text(json.dumps(SHOTS, indent=2)+'\n')
