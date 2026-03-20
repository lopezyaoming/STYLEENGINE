# Spiridellis Bros. Studios: ART BIBLE v1
**Document Owner:** Lead Creative Technologist  
**Status:** Active Draft (Synthesized from Miro Board Notes - 10/2025)

---

## 1. CORE VISUAL DIRECTION
Our goal is to push past "middle-ground Disney-basic" and get **weirder and funkier** with our designs. We are heavily inspired by the mixed-media, collage-in-motion aesthetic of artists like **Ariel Costa (Blink My Brain)**. The visual target is a stylized, tactile hybrid of 3D modeling and 2D compositing, heavily utilizing 2.5D spatial layouts (3D tubes, ground planes, and layered 2D cards) with a tone that is *"slightly TOO aggressive, but funny."*

---

## 2. TECHNICAL SHADING & RENDER GUIDELINES

### The "Plasticness" Material Standard
A recurring favorite from the visual development phase is a highly tactile "plasticness" for our 3D elements. To achieve this designer-toy/vinyl feel in Blender (Cycles/Eevee), adhere to the following Principled BSDF parameters:
*   **Base Color:** High saturation, distinct values.
*   **Specular:** `0.8 - 1.0` (We want a sharp, punchy highlight).
*   **Roughness:** `0.15 - 0.25` (Keep it smooth, but not perfectly mirror-like; add slight surface imperfection maps if necessary).
*   **Subsurface Scattering (SSS):** Weight set to `0.15 - 0.35`. Use a warmer tint (red/orange) for the Subsurface Color to give the plastic a slightly luminous, dense, and "gummy" light-bleed under rim lighting. Scale to match the asset's real-world micro-scale.

### The "Boiling Line" Requirement
To seamlessly integrate 3D elements with 2D character comps and retain a hand-crafted, kinetic energy, all stroke outlines must employ a **Boiling Line**.
*   **Variance:** Line weight must continuously oscillate between **3px and 8px**.
*   **Implementation:** Use Blender's Grease Pencil `Line Art` modifier with a `Noise` modifier applied to the thickness.
*   **Framerate:** Bake the noise evaluation to step on twos (or roughly 12fps) to simulate traditional traditional cel-animation imperfections.

---

## 3. CHARACTER PIPELINES & AESTHETICS

### Black Hamster
**Tone/Aesthetic:** Gritty, slightly aggressive, but inherently comedic. 
**Rigging & Animation Verdict (Simplicity First):**
*   **Body & Head:** Separate the head from the body to avoid complex weight painting. Parent both to their own master empties.
*   **Arms & Legs:** *No full IK armature.* Parent limbs at the shoulder/hip to an empty. Swap assets when he hits the ground (e.g., swapping a swinging leg for an anchored foot). Counter-animate manually, except for cockpit shots where hands should be parented to the steering yoke.
*   **Face:** Avoid complex facial rigs. Use **Shape Keys** for fast, snappy animation (e.g., spitting out the seed). 
*   **Jacket / Cloth:** *NO CLOTH SIMULATIONS.* Cloth sim creates production friction. We are pivoting to a **shorter jacket** with a few controller bones/shape keys to manipulate the silhouette. Since it's dark black, we don't need interior crease detail—just silhouette breakup. 

### Underwear Frog
**Tone/Aesthetic:** Embracing the directive to "get much weirder," Underwear Frog represents the peak of our funky, off-kilter design ethos. 
*   **Visual Execution:** He should heavily utilize the **"Plasticness"** shader, contrasting his glossy, gummy-toy rendering with the aggressive **3px-8px Boiling Line**. 
*   **Design Details:** Bulbous, asymmetrical proportions. The "underwear" should look hand-drawn/2D and projected onto the 3D geometry to push the Ariel Costa-style mixed-media aesthetic. His movements should feel staccato and erratic, emphasizing the comedic absurdity of his design.

### Neon Gerbil
**Tone/Aesthetic:** The elusive speedster. 
*   **Visual Execution:** For the majority of the environment shots, Neon Gerbil should be rendered as a glowing, neon blur zipping through the city. Keep the actual character geometry hidden to build a visual question, only fully "revealing" the sharp, plastic model during the interior cockpit cutaway.

---

## 4. ENVIRONMENT & LAYOUT PIPELINE
The world is a gritty, atmospheric "Rodent City"—a mashup of Times Square and a dirty pet cage. 
*   **Set Construction:** Build scenes as **2.5D Layouts**. Use a 3D ground plane and 3D hero elements (like hamster tubes), but carve the background and foreground up into 2D layers (image gen/painted cards).
*   **Lighting & Atmosphere:** Heavy middle-ground fog to obscure distant city details. Use live-action overlay footage for smoke/mist trails from chimneys, and potentially rain.
*   **Key Landmarks:** 
    *   *The Big Boss Tower:* The single tallest building in the far BG, topped with a glowing neon sign.
    *   *Streets:* Gritty city elements mixed with wood chips and cage bedding piled up like street snow. 
    *   *Lighting:* Set up rigs to easily control city lights blinking on/off and changing colors to interact with the neon glow of the characters.

---
*Note to Animators: Keep it scrappy, keep it stylized. If a shot takes more than 4 hours to layout and render for paint, simplify the approach.*