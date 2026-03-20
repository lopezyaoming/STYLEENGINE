# DESCRIPTIVE.MD: VISUAL SYSTEM AUTOPSY

## COGNITIVE TOPOLOGY
The mental mapping of the project reveals a highly specific, dual-nature production philosophy. The creative cognition of the team is structured around the deliberate collision of disparate visual and narrative systems, balanced by strict pipeline optimization.

**Logical Clusters:**
*   **The "Tactile Diorama" Cluster:** Environmental cognition operates on the concept of miniaturization. Massive, gritty, urban or industrial concepts (slums, refineries, sci-fi cities) are mentally processed as physical, tabletop models. The logic dictates that environments possess the properties of manufactured toys rather than actual architecture.
*   **The "Kinetic Absurdity" Cluster:** Character design and action logic center on subversion. Entities built from cute, non-threatening primitives (spherical rodents, gummy bears) are mapped into hyper-aggressive, noir, or high-stakes action scenarios. The cognitive approach to animation prioritizes squash-and-stretch elasticity and graphical smearing over anatomical logic.
*   **The "2.5D Spatial" Cluster:** Pipeline thinking relies heavily on hybrid methodologies. The team cognitively separates spatial mapping from aesthetic finishing. Environments are constructed as flat 2D planes mapped into 3D volumetric "tubes" or sequences to achieve perfect parallax, while characters fluctuate between 2D sketches and optimized 3D proxy models.

**Anchor Assets:**
*   **The "Plasticness" Look-Dev Renders:** A series of material tests that lock in the exact specular response and subsurface scattering values required to make industrial pipes and slums read as molded vinyl/plastic.
*   **The "Black Hamster" and "Neon Gerbil" Storyboards:** Foundational narrative anchors that establish the cinematic pacing logic (the "Tease and Reveal" or "Question and Answer" rhythm) and the extreme scale contrast between vast, dark environments and tiny, hyper-emissive subjects. 

**Friction Points:**
*   **Simulation vs. Stylization:** A persistent cognitive friction exists between 3D software defaults (cloth simulation, complex bone-weighting, realistic physics) and the intended stylized 2D/cartoon aesthetic. The team actively devises "hacks" (using shape keys instead of cloth physics, severing character heads from bodies to avoid neck deformation) to bypass the 3D engine's inherent realism.
*   **Atmosphere vs. Readability:** The desire for a moody, fog-choked, deep-shadowed environment ("Cyberpunk/Noir") constantly fights the necessity for character readability. This friction is resolved through the application of the "plastic" material shaders and extreme, localized emissive lighting, which force object silhouettes to pop through the visual noise.

## MATERIAL & SURFACE AUTOPSY
The physics of the world operate under a highly controlled, synthetic ruleset that actively rejects photorealistic material decay. 

**Physics of Light:**
*   **Volumetric Supremacy:** Atmosphere is treated as a dense, physical medium. Light does not travel in a vacuum; it aggressively scatters, creating thick, luminous fog, localized bloom, and heavy halation around emissive sources. This atmospheric perspective is the primary tool for establishing depth and scale, frequently washing out background architecture entirely.
*   **High-Contrast Emissives:** The world is perpetually low-key (dark). Primary illumination is diegetic, driven by intensely saturated neon point lights (toxic greens, magentas, harsh oranges) that puncture the ambient darkness. 
*   **Chiaroscuro & Artificial Rim Lighting:** Light behaves theatrically. Scenes rely on solid, crushed black shadows. Colored rim lights are applied artificially to separate foreground silhouettes from background masses, regardless of environmental light logic.

**Surface Shaders & Materiality:**
*   **The "Plastic" Specular Response:** The dominant surface characteristic is a smooth, broad, semi-glossy specular highlight. Materials that represent metal, concrete, or stone are shaded with low surface roughness and zero metallicity. Light glides over the geometry, accurately mimicking the light response of injection-molded PVC, vinyl toys, or thick enamel paint.
*   **Subsurface Scattering (SSS):** Translucency is highly active in the structural geometry. Industrial pipes, tubing, and character appendages absorb and scatter light internally, creating a dense, gummy, or jelly-like luminescence rather than a hard, opaque bounce.
*   **Absence of High-Frequency Detail:** Micro-textures (pores, rust flakes, granular grit) are actively suppressed. Where "grime" or "wear" exists, it is applied as broad, smooth color variations rather than physical displacement or bump mapping.

## GEOMETRIC ARCHITECTURE
Form and volume are manipulated to create a distinct, non-literal reality that emphasizes readability and chunkiness.

**Character Form:**
*   **Hyper-Primitive Foundations:** Biological anatomy is entirely discarded. Characters are constructed from unified spheres, ovoids, and "bean" shapes. Head and torso masses are synthesized into a single continuous volume.
*   **Vestigial Appendages:** Limbs and extremities are reduced to tiny, non-articulated cylinders or simple spheres protruding directly from the central core mass, resulting in extreme "chibi" or top-heavy proportions.

**Environmental Form:**
*   **Chunky Brutalism:** Architectural elements are massive and heavily simplified. The ratio of detail to surface area is extremely low.
*   **Macro-Beveling:** Sharp, 90-degree mathematical corners do not exist. All edges, joints, flanges, and structural intersections are aggressively rounded and filleted, enforcing the visual logic of injection molding where sharp edges are physically impossible.
*   **Non-Euclidean Distortion:** The geometry exhibits organic warping. Buildings lean, taper, and bulge. Straight lines are avoided in favor of subtle S-curves and drooping arcs, even in rigid industrial objects like scaffolding or plumbing.

## GRAPHIC BOUNDARIES
The definition of edges transitions fluidly based on the pipeline stage, ultimately resulting in a system where silhouette is the primary communicant of data.

**Silhouette Logic:**
*   **Boundary as Data:** Because surface texture is minimized, the outer contour of an object carries the total burden of identification. Silhouettes are highly distinct and exaggerated, designed to remain instantly readable even when rendered as pure black against a bright background or shrunk to a fraction of the screen size.
*   **Negative Space Framing:** The system utilizes heavy, dark foreground masses (arches, pipes, looming figures) to create strict, contained negative space that acts as a physical vignette, forcing the viewer's eye toward specific, bright internal boundaries.

**Linework and Edge Behavior:**
*   **Pre-visualization (2D):** In the layout and storyboard phases, line behavior is "searching," erratic, and rough. It utilizes varying pressure and overlapping, scratchy strokes to map out kinetic energy and directional vectors rather than defining clean geometry.
*   **Final Output (3D/2.5D):** Drawn contour lines are almost entirely erased. Boundaries are defined exclusively by value contrast (a brightly lit edge meeting a dark shadow) and color blocking. Edges are soft, blending into the atmospheric fog, creating a painterly transition between objects and space.
*   **Kinetic Abstraction:** High-speed motion is not represented by physical geometry. It is translated into pure, flat, graphic vectors—represented by sweeping, tapered lines, neon smears, or sharp parallel hatching that overrides the underlying 3D forms.