# SPIRIDELLIS BROS. STUDIOS
## PRODUCTION ART BIBLE v1.0
**Compiled by:** Lead Creative Technologist
**Date:** October 2025
**Core Inspirations:** Ariel Costa / Blink My Brain, Mixed-Media Collage, 2.5D Environments

---

## 1. CORE VISUAL IDENTITY & PIPELINE

Our visual goal is a highly stylized, tactile, and slightly unhinged aesthetic ("slightly TOO aggressive but funny"). We are utilizing a hybrid 2D/3D pipeline inside Blender to achieve a handmade, mixed-media feel on a shoestring budget. 

**The Golden Rule of this Production:** *Simplicity over Simulation.* 
Avoid production friction. We are prioritizing smart, snappy shape keys and clever 2D compositing over heavy physics or weight painting.

---

## 2. THE "PLASTICNESS" SHADER STANDARD

A recurring note across visual development is the love for the "plasticness" of our character renders. To standardize this toy-like, vinyl aesthetic across the team, all primary character Base Materials in Blender (Principled BSDF) must adhere to the following baseline parameters:

*   **Specular:** `0.650 - 0.800` (We want sharp, localized light catches that emphasize curvature).
*   **Roughness:** `0.200 - 0.350` (Glossy, but not a perfect mirror. It needs to feel like manufactured vinyl or hard rubber).
*   **Subsurface Scattering (SSS):** `0.150 - 0.250` (Crucial. This gives the geometry that dense, light-absorbing toy quality).
*   **Subsurface Radius:** Adjusted per character scale, but heavily weighted toward warm (red/orange) underlying tones to give life to the characters without making them look fleshy.
*   **Clearcoat:** `0.05` (Optional, use sparingly only on eyes or wet elements).

---

## 3. LINEWORK: THE "BOILING LINE" REQUIREMENT

To mesh our 3D geometry with Ariel Costa-style 2D environments and rough composites, all characters and foreground interactive objects must feature a continuous "Boiling Line."

*   **Line Variance:** Every stroke must dynamically fluctuate between **3px and 8px**.
*   **Execution (Blender Grease Pencil / Line Art Modifier):** 
    *   Apply a **Noise Modifier** to the line thickness and position.
    *   **Stepping:** The noise seed must change on 2s or 3s (12fps or 8fps equivalent) to break the smooth interpolation of 3D. 
    *   This gives the characters a nervous, hand-drawn kinetic energy that matches the "aggressive but funny" tone.

---

## 4. CHARACTER AESTHETICS & RIGGING SPECS

### BLACK HAMSTER
**Aesthetic:** 
Dark, gritty, and unified. A chunky silhouette where the head and body unify but retain form. He wears a dark black jacket and a bandoleer. Because his palette is pitch black, we will not pick up crease details within the shape�rely entirely on the silhouette and the 3px-8px boiling line to define his volume. 

**Rigging & Animation Needs (The "Shoestring" Method):**
*   **NO CLOTH SIMULATION.** Cloth sim is production friction.
*   **Jacket:** Shortened from early concept art. It drags slightly on the floor to allow for dramatic extension during action sequences. Driven entirely by **Shape Keys** to affect the silhouette.
*   **Body Structure:** Separate the head from the body. Parent both to their own Empties to avoid weight painting complications. 
*   **Limbs:** No complex IK/FK rigs needed for standard shots. Arms and legs are simple geometry parented at the shoulder/hip to Empties. They only need the ability to go from straight to bent (scale/rotate). *Note: Swap leg assets when he hits the ground so they are anchored at the feet.*
*   **Face:** Most shots are too fast for detailed lip-sync. Use **Shape Keys** for specific narrative beats (e.g., spitting out the seed). 

### UNDERWEAR FROG
**Aesthetic:** 
The comedic foil. If Black Hamster is gritty shadow, Underwear Frog is bright, pathetic exposure. He must perfectly embody the "Plasticness" spec outlined above�highly subsurface-scattered, squishy-looking green vinyl skin. He wears tight-fitting classic white briefs (tighty-whities). 
*   **Design Note:** The underwear should look like it is riding up slightly too high. 
*   **Technical:** Keep the underwear as integrated geometry (no cloth sim). The high spec/low roughness of his skin should sharply contrast with a matte, rough shader on the underwear.

### NEON GERBIL
**Aesthetic:** 
The elusive target. For the first two acts, he is strictly a "glowing blur" zipping through the city. 
*   **Technical:** Use a high-intensity Emission shader mixed with heavy motion blur. Set up the visual question first. Do not reveal his true form until the climax cockpit shot.

---

## 5. ENVIRONMENT & CAMERA LAYOUT

The world is a gritty, atmospheric rodent metropolis�a mix of modular hamster tubes and dark, rainy city streets where wood chips and cage bedding are piled up like snow.

**Environment Pipeline:**
*   **Foreground / Midground:** 3D hamster tubes and specific hero props (modeled in Gravity Sketch / Blender). 
*   **Background:** 2D painted planes and cards carved up into layers to allow for parallax.
*   **Lighting & FX:** Heavy middle-ground volumetric fog to obscure city details (saving paint time). High-angle camera shots looking down. Distant neon signs (boss towers) poking through the fog. 
*   **Post/Compositing:** Overlay live-action video footage of rain, smoke, and mist trails between buildings to quickly achieve high-fidelity texture. Layout cameras in Blender sub-4 hours, render to flat layers, and paint.