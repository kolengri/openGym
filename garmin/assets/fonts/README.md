# Dashboard label font

The unmodified `IBMPlexMono-Medium.woff2` originates from Google Fonts' IBM Plex
Mono family (IBM, SIL Open Font License 1.1). The bundled OFL.txt contains the
copyright and license terms. Source: https://github.com/google/fonts/tree/main/ofl/ibmplexmono

The source contains the Latin and Cyrillic glyphs used in the English/Russian
dashboard. The generated bitmap assets are named OpenGym Mono. Four sizes keep
labels readable on the 454-pixel AMOLED and 280-pixel Solar targets without
allocating native oversized label fonts.

To regenerate, create a local virtual environment, install `requirements.txt`, and
run `scripts/garmin-fonts.py` from the repository root. Pillow rasterizes glyphs;
fontTools and Brotli decode the source WOFF2. The generator writes standard
AngelCode BMFont text descriptors and grayscale PNG masks into
`garmin/resources/fonts/`. Connect IQ recolors these masks while drawing.

No font-generation dependency is included in the watch runtime. Keep the source
font and OFL notice with redistributed source and generated font assets.
