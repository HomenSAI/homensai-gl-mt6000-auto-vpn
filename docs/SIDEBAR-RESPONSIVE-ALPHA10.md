<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Sidebar accessibility - alpha10

The sidebar adapts to the actual available viewport height and external fixed/sticky headers. It has no fixed minimum height that can push Settings off-screen. Branding/footer remain stable; the menu gets independent vertical scrolling when it cannot fit. On exceptionally short desktop panels the whole sidebar scrolls. On mobile the nine navigation links wrap instead of hiding the last items in a single horizontal strip. Active links are revealed in the nav without a document jump; the nav can be focused and scrolled by keyboard.

Browser matrix: nine pages x eight viewport dimensions x English/Russian = 144 transitions. All active links remained inside their menu and visible after navigation; no root horizontal overflow. Sizes: 978x808, 1280x720, 1024x600, 800x480, 640x360, 414x896, 360x640, 1280x300. 640x360 is a zoom-equivalent CSS-area check, not a claim of changing/testing the browser's native zoom setting. Home/PageDown keyboard scroll also passed. See qa/ui-review-alpha10/menu-matrix.json and screenshots.

Tables may scroll inside their own containers when data is wider than the screen; this is intentional and does not hide navigation. The physical router was not touched. New dashboard40/ui21 asset URLs avoid masking the correction with cached alpha9 resources.
