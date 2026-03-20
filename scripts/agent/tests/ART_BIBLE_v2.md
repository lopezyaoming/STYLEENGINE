# Spiridellis Bros. Studios: ART BIBLE v2
**Document Owner:** Lead Creative Technologist  
**Status:** Approved for Production (Updated & Synthesized from Visual Audit - 10/2025)

---

## 1. CORE AESTHETIC PILLARS
Based on rigorous visual auditing and look-development testing, we have moved past "middle-ground Disney-basic" and crystallized our visual DNA. All assets, layouts, and animations must strictly adhere to the following four pillars:

**I. Tactile Plasticity & Miniature Scale (The Diorama Effect)**  
The world is a physical, manufactured playset. We reject photorealistic grit, high-frequency rust, and sharp industrial metal. Instead, surfaces must read as injection-molded plastic, vinyl, or painted clay. Deep, shallow Depth of Field (macro-lens/tilt-shift) must be employed to force a "miniature toy" scale.

**II. High-Contrast Neon-Noir Atmosphere**  
Environments rely on dense volumetric fog and atmospheric perspective. The world is primarily dark (chiaroscuro shadows, deep cool purples/blues) punctured aggressively by hyper-saturated, glowing emissive light sources (toxic greens, hot pinks, warning oranges).

**III. Aggressive Absurdism (Shape & Tone Juxtaposition)**  
Character shape language relies on soft, bottom-weighted, "chunky" spheres and pill shapes (inherently cute). This must be radically juxtaposed with intense, highly angular facial expressions, gritty cinematic framing, and exaggerated emotional reactions. The tonal mandate is: *"Slightly TOO aggressive, but funny."*

**IV. Mixed-Media 2.5D Spatiality**  
Heavily inspired by Ariel Costa (Blink My Brain), our scenes are collages in motion. We construct layouts using flat 2D background planes interacting with volumetric 3D hero objects (e.g., 3D tubes navigating through 2D painted cards) to create a distinct pop-up book parallax.

---

## 2. SHADER & TEXTURE SPECS

### The "Plasticness" Material Standard
All 3D environmental assets and character bodies must utilize our custom "Plasticness" Principled BSDF shader parameters in Blender (Cycles/Eevee):
*   **Surface Smoothness:** *Zero high-frequency micro-details.* Do not use porous concrete, sharp metal scratches, or grain normal maps. Grime should feel "painted on" rather than structurally etched.
*   **Specular:** `0.8 - 1.0`. We require broad, distinct, slightly soft glossy highlights.
*   **Roughness:** `0.15 - 0.25`. Smooth, but not perfectly mirror-like.
*   **Subsurface Scattering (SSS):** Weight set to `0.15 - 0.35`. Use warmer tints (reds/oranges/yellows) for the Subsurface Color to mimic thick, gummy vinyl or light bleeding through acrylic.
*   **Edge Geometry:** *No sharp 90-degree corners.* All hard-surface assets (buildings, pipes, machinery) must have thick, rounded bevels to mimic injection-molded toy manufacturing. "Thickness of elements needs to be thick enough, not thin & flimsy."

### Emissive & Neon Shaders
*   Neon elements must act as primary practical lights. Use high emission strength coupled with Bloom (in Eevee) or Glare compositing nodes to create a "glowing blur" effect.
*   Translucent plastics (e.g., gerbil tubes) must utilize volumetric scatter or transmission to diffuse internal light sources softly.

---

## 3. LINE & OUTLINE LOGIC

### The "Boiling Line" Mandate
To bridge the gap between our 3D volumetric assets and 2D mixed-media elements, all character outlines and distinct 2D UI/VFX elements must employ a **Boiling Line**.
*   **Thickness Variance:** Line weight must continuously oscillate between **3px and 8px**.
*   **Implementation Engine:** Utilize Blender's Grease Pencil `Line Art` modifier driven by a `Noise` modifier applied to the stroke thickness and position.
*   **Framerate Simulation:** The noise evaluation must be baked to step on twos (approx. 12fps) to simulate the imperfect, hand-drawn jitter of traditional cel animation.
*   **Silhouetting Rule:** In extreme lighting conditions, drop interior linework entirely and render characters as pure, stark black silhouettes against bright backgrounds to emphasize graphic shape language. 

---

## 4. ASSET HIERARCHY & RIGGING RULES

**SIMPLICITY OVER SIMULATION.** We are operating on a stylized, rapid-iteration pipeline. If a rig or simulation takes more than 4 hours to troubleshoot per shot, simplify the approach.

### Character Rigging Logic
*   **No Cloth Simulations:** Cloth sims create unacceptable production friction and break the chunky aesthetic. Garments (like the Black Hamster's jacket) must be modeled thick and rigged with basic controller bones or shape keys to manipulate the silhouette. *Note: Jackets must drag slightly on the floor to allow animators to extend the shape dynamically during action.*
*   **Mesh Separation:** Decouple heads, bodies, and limbs into separate meshes where necessary to avoid complex, stretching weight-painting on "blobby" characters. 
*   **Limb Hierarchies:** Avoid full complex armature IK chains for stubby limbs. Parent separated arm/leg geometry to empties at the shoulder/hip. Use IK *only* for feet planting on uneven terrain (e.g., rocky ground). 
*   **Facial Animation:** Do not use complex bone-driven face rigs. Build primary expressive poses (neutral, furious, screaming) and utilize **Shape Keys** to snap between them for snappy, comedic timing.

---

## 5. ENVIRONMENT & LAYOUT PIPELINE

### 2.5D Scene Construction (The "Card & Tube" Method)
All environments are built for camera projection and parallax, not as fully explorable 3D worlds.
*   **Foreground/Midground:** Place fully volumetric 3D assets (hero characters, sweeping cylindrical pipes, the "Big Boss Tower") in the immediate playable space.
*   **Background:** Carve background architecture and skylines into flat 2D image planes (Cards). Stack these planes along the Z-axis.
*   **Atmospheric Separation:** Place dense Volumetric Fog/Mist between the 2D cards and 3D foreground objects. The midground fog must obscure ground-level city details to save modeling time and force the "towering" scale. 

### Narrative Staging Directives
*   **The "Neon Gerbil" Setup Rule:** For action sequences involving the speedster character, adhere to a strict Question/Answer visual structure:
    *   *The Setup (Question):* Keep the subject unrevealed. Show it as a high-speed "glowing blur" or a distant point of light zipping through the massive, dark city layout.
    *   *The Payoff (Answer):* Hard cut to a tight, highly detailed "cockpit shot" inside the vehicle, utilizing extreme color contrast (neon green character vs. dark grey machinery) to reveal the chaotic action.